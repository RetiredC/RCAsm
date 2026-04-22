// (c) RetiredCoder, 2026

#include "cuda_runtime.h"
#include "device_launch_parameters.h"

#include <stdio.h>
#ifdef _WIN32
#include <Windows.h>
#endif

#include "CallCubin.h"
#pragma warning(disable : 4996)

#include "kernel.cu"
#include "Ec.h"

#include <string.h>

#ifdef _WIN32
#include <windows.h>
#include <profileapi.h>
#else
#define MAX_PATH 512
typedef unsigned char BYTE;
#include <unistd.h>
#include <limits.h>
#include <time.h>
#endif

int smCnt;
int test_sm = 0;

static uint64_t start_time[64];

#ifdef _WIN32
static LARGE_INTEGER g_freq;
#endif

void InitTimers(void)
{
#ifdef _WIN32
	QueryPerformanceFrequency(&g_freq);
#endif
}

static uint64_t GetTimeMicroseconds(void)
{
#ifdef _WIN32
	LARGE_INTEGER t;
	QueryPerformanceCounter(&t);
	return (uint64_t)((1000000ULL * (uint64_t)t.QuadPart) / (uint64_t)g_freq.QuadPart);
#else
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint64_t)ts.tv_sec * 1000000ULL + (uint64_t)ts.tv_nsec / 1000ULL;
#endif
}

void StartTimer(int TimerIndex)
{
	start_time[TimerIndex] = GetTimeMicroseconds();
}

int GetTimer(int TimerIndex) // in microseconds
{
	uint64_t now = GetTimeMicroseconds();
	return (int)(now - start_time[TimerIndex]);
}

void GetCurrentDir(char* path)
{
	path[0] = 0;

#ifdef _WIN32
	DWORD len = GetModuleFileNameA(NULL, path, MAX_PATH);
	if (len == 0 || len >= MAX_PATH)
		return;

	char* last_slash = strrchr(path, '\\');
	if (last_slash)
		*last_slash = 0;
#else
	ssize_t len = readlink("/proc/self/exe", path, PATH_MAX - 1);
	if (len <= 0 || len >= PATH_MAX - 1)
		return;

	path[len] = 0;

	char* last_slash = strrchr(path, '/');
	if (last_slash)
		*last_slash = 0;
#endif
}

#ifdef _WIN32
    #include <sys/stat.h>
    bool file_exists(const char* path)
    {
        struct _stat st;
        return _stat(path, &st) == 0;
    }
#else
    #include <sys/stat.h>
    bool file_exists(const char* path)
    {
        struct stat st;
        return stat(path, &st) == 0;
    }
#endif

// :)
uint get_rnd32()
{
	return (rand() & 0xFF) | ((rand() & 0xFF) << 8) | ((rand() & 0xFF) << 16) | ((rand() & 0xFF) << 24);
}


//256bits = 32bytes
#define BYTES_32		32

int getdifind(void* a, void* b)
{
	BYTE* aa = (BYTE*)a;
	BYTE* bb = (BYTE*)b;
	for (int i = 0; i < 32; i++)
		if (aa[i] != bb[i])
			return i;
	return 64;
}

bool CheckResults(uint* a, uint* b, uint* c, int size) //check "MulMod256"
{
	EcInt a8, b8, true8, r8;
	int failed_ind = -1;
	for (int i = 0; i < size; i++)
	{
		memcpy(a8.data, a + 8 * i, 32);
		memcpy(b8.data, b + 8 * i, 32);
		memcpy(r8.data, c + 8 * i, 32);
		  
		true8 = a8;
		true8.MulModP(b8);

		if (memcmp(true8.data, r8.data, 32))
		{
			int ind = getdifind(true8.data, r8.data);
			failed_ind = i;
			break;
		} 

	}
	if (failed_ind < 0)
		printf("CHECKRES OK\r\n");
	else
		printf("CHECKRES FAILED at index %d\r\n", failed_ind);
	return failed_ind < 0;
}

bool TestKernel(int RepeatCnt)
{
	const int size = 256 * 128;
	uint* a = (uint*)malloc(size * BYTES_32);
	uint* b = (uint*)malloc(size * BYTES_32);
	uint* c = (uint*)malloc(size * (BYTES_32*2 + 16));

	for (int i = 0; i < size; i++)
	{
		for (int j = 0; j < 8; j++)
		{
			a[8 * i + j] = get_rnd32();
			b[8 * i + j] = get_rnd32();
		}
	}
	int mcs;
	double mspeed;
	kparams params;
	params.dev_a = 0;
	params.dev_b = 0;
	params.dev_c = 0;
	params.repeat_cnt = RepeatCnt;
	cudaError_t cudaStatus;

	TCubinCall cc;
	TCallKernelParams kp;

	char fn[MAX_PATH], path[MAX_PATH];

	if (test_sm == 120)
		strcpy(fn, "/kernel_sm120.cubin");
	else
		strcpy(fn, "/kernel_sm89.cubin");

	GetCurrentDir(path);
	strcat(path, fn);
	if (!file_exists(path))
	{
		GetCurrentDir(path);
		strcat(path, "/..");
		strcat(path, fn);
	}

	if (!cc.LoadCubin(path))
		return false;

	cudaStatus = cudaMalloc((void**)&params.dev_a, size * BYTES_32);
	if (cudaStatus != cudaSuccess) 
	{
		fprintf(stderr, "cudaMalloc1 failed!");
		goto Error;
	}
	cudaStatus = cudaMalloc((void**)&params.dev_b, size * BYTES_32);
	if (cudaStatus != cudaSuccess) 
	{
		fprintf(stderr, "cudaMalloc2 failed!");
		goto Error;
	}
	cudaStatus = cudaMalloc((void**)&params.dev_c, size * BYTES_32);
	if (cudaStatus != cudaSuccess) 
	{
		fprintf(stderr, "cudaMalloc3 failed!");
		goto Error;
	}

	cudaStatus = cudaMemcpy(params.dev_a, a, size * BYTES_32, cudaMemcpyHostToDevice);
	if (cudaStatus != cudaSuccess) 
	{
		fprintf(stderr, "cudaMemcpy failed!");
		goto Error;
	}

	cudaStatus = cudaMemcpy(params.dev_b, b, size * BYTES_32, cudaMemcpyHostToDevice);
	if (cudaStatus != cudaSuccess) 
	{
		fprintf(stderr, "cudaMemcpy failed!");
		goto Error;
	}

	strcpy(kp.kernel_name, "mulKernel");
	kp.blockSize = 256;
	kp.blockCnt = smCnt;
	kp.sharedSize = 0;
	kp.stream = NULL;
	kp.kernel_param_ptr = &params;
	kp.kernel_param_size = sizeof(params);

	StartTimer(0);
	if (!cc.CallKernel(kp))
	{
		fprintf(stderr, "CallKernel failed!");
		goto Error;
	}

	cudaStatus = cudaGetLastError();
	if (cudaStatus != cudaSuccess) 
	{
		fprintf(stderr, "mulKernel launch failed: %s\n", cudaGetErrorString(cudaStatus));
		goto Error;
	}

	cudaStatus = cudaDeviceSynchronize();
	if (cudaStatus != cudaSuccess) 
	{
		fprintf(stderr, "cudaDeviceSynchronize returned error code %d after launching mulKernel! %s\n", cudaStatus, cudaGetErrorString(cudaStatus));
		goto Error;
	}

	mcs = GetTimer(0);
	printf("\r\nKernel time: %d mcs\r\n", mcs);
	mspeed = (((double)params.repeat_cnt) * 256 * smCnt) / mcs; //speed in MH
	printf("Speed: %f GMul\r\n", mspeed/1000);

	cudaStatus = cudaMemcpy(c, params.dev_c, size * BYTES_32, cudaMemcpyDeviceToHost);
	if (cudaStatus != cudaSuccess) 
	{
		fprintf(stderr, "cudaMemcpy failed!");
		goto Error;
	}

Error:
	cudaFree(params.dev_c);
	cudaFree(params.dev_a);
	cudaFree(params.dev_b);

	if (cudaStatus != cudaSuccess) 
	{
		fprintf(stderr, "mulKernel failed!");
		return false;
	}

	bool res = CheckResults(a, b, c, size);
	return res;
}

int main(int argc, char* argv[])
{
	if ((argc > 1) && (strcmp(argv[1], "-test_sm") == 0))
		test_sm = atoi(argv[2]);

	InitEc();
	InitTimers();
	::cuInit(0);

	int GpuCnt = 0;
	cudaError_t error_id = ::cudaGetDeviceCount(&GpuCnt);
	if (error_id != cudaSuccess)
	{
		printf("CUDA Init Error: %d\n", error_id);
		return false;
	}
	if (!GpuCnt)
	{
		printf("No GPU found\n");
		return false;
	}
	int GpuInd = -1;
	for (int i = 0; i < GpuCnt; i++)
	{
		cudaSetDevice(i);
		cudaDeviceProp deviceProp;
		cudaGetDeviceProperties(&deviceProp, i);
		printf("GPU %d: %s, %.2f GB, %d CUs, cap %d.%d\r\n", i, deviceProp.name, ((float)(deviceProp.totalGlobalMem / (1024 * 1024))) / 1024.0f, deviceProp.multiProcessorCount, deviceProp.major, deviceProp.minor);
		int cm = deviceProp.major * 10 + deviceProp.minor;
		if ((cm != 89) && (cm != 120))
		{
			printf("GPU %d - not supported, skip\r\n", i);
			continue;
		}
		if (test_sm && (cm != test_sm)) //for asm kernel tests from RCAsm
		{
			printf("GPU %d - test_sm, not matched, skip\r\n", i);
			continue;
		}

		//if (deviceProp.multiProcessorCount > 180)
		//	continue; //skip 6000pro

		smCnt = deviceProp.multiProcessorCount;
		GpuInd = i;
		break;
	}
	if (GpuInd < 0)
	{
		printf("No matched GPU found\n");
		return false;
	}

///////////
	int repeat_cnt = 1;
	if (TestKernel(repeat_cnt))
		printf("TestKernel(%d) OK", repeat_cnt);
	else
	{
		printf("TestKernel(1) FAILED");
		return 0;
	}
	    
	repeat_cnt = 30 * 10000;
	if (TestKernel(repeat_cnt))
		printf("TestKernel(%d) OK", repeat_cnt);
	else
		printf("TestKernel FAILED !!!");

	return 0;
}
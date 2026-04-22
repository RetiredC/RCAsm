// (c) RetiredCoder, 2026

#include "CallCubin.h"
#include <stdio.h>
#pragma comment(lib, "cuda.lib")
#pragma warning(disable : 4996)

TCubinCall::TCubinCall()
{
	cuModule = NULL;
}

TCubinCall::~TCubinCall()
{
}

bool TCubinCall::LoadCubin(const char* fn)
{
	CUresult res = ::cuModuleLoad(&cuModule, fn);
	if (res != CUDA_SUCCESS)
	{
		printf("cuModuleLoad Error: %d\n", res);
		return false;
	}
	return true;
}

bool TCubinCall::CallKernel(TCallKernelParams params)
{
	dim3 gridDim, blockDim;
	gridDim.x = params.blockCnt; gridDim.y = 1; gridDim.z = 1;
	blockDim.x = params.blockSize; blockDim.y = 1; blockDim.z = 1;

	int ArgCnt = 1;
	void** args = (void**)malloc(8 * ArgCnt);
	if (!args)
		return false;
	for (int i = 0; i < ArgCnt; i++)
		args[i] = params.kernel_param_ptr;

	CUfunction f;
	CUresult res = ::cuModuleGetFunction(&f, cuModule, params.kernel_name);
	if (res != CUDA_SUCCESS)
	{
		free(args);
		printf("cuModuleGetFunction failed, err %d\r\n", res);
		return false;
	}

	res = ::cuLaunchKernel(f, gridDim.x, gridDim.y, gridDim.z, blockDim.x, blockDim.y, blockDim.z, params.sharedSize, params.stream, args, NULL);
	free(args);

	if (res != CUDA_SUCCESS)
	{
		printf("cuLaunchKernel failed, err %d\r\n", res);
		return false;
	}
	return true;
}
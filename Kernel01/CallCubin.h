// (c) RetiredCoder, 2026

#pragma once
#ifdef _WIN32
#include <Windows.h>
#endif
#include "cuda_runtime.h"
#include "cuda.h"

struct TCallKernelParams
{
	char kernel_name[256];
	int blockSize;
	int blockCnt;
	int sharedSize; //LDS size
	cudaStream_t stream;
	void* kernel_param_ptr;
	int kernel_param_size;
};

class TCubinCall
{
private:
	CUmodule cuModule;

public:
	TCubinCall();
	~TCubinCall();

	bool LoadCubin(const char* fn);
	bool CallKernel(TCallKernelParams params);
};


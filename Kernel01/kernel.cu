
typedef unsigned int uint;
typedef unsigned long long u64;

struct kparams
{
	uint* dev_a;
	uint* dev_b;
	uint* dev_c;
	uint repeat_cnt;
};


#ifdef __CUDA_ARCH__
extern "C" __global__ void mulKernel(kparams params)
{ 
//dummy
params.dev_c[0] = params.dev_a[0] * params.dev_b[0];
}
#endif
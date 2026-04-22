cmake_minimum_required(VERSION 3.17)

project(mbench LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CUDAToolkit_ROOT /usr/local/cuda-12.8)

find_package(CUDAToolkit REQUIRED)

set(THREADS_PREFER_PTHREAD_FLAG TRUE)
find_package(Threads REQUIRED)

add_executable(mbench
    main.cpp
    CallCubin.cpp
    Ec.cpp
    utils.cpp
)

target_link_libraries(mbench PRIVATE
    CUDA::cudart
    CUDA::cuda_driver
    Threads::Threads
)

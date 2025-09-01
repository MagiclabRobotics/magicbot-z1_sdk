/*
 * @FilePath: /humanoid_m1_sdk/sdk/include/magic_export.h
 * @Version: 1.0.0
 * Copyright © 2025 MagicLab.
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#if defined _WIN32 || defined __CYGWIN__
  #ifdef __GNUC__
    #define MAGIC_EXPORT_API __attribute__((dllexport))
  #else
    #define MAGIC_EXPORT_API __declspec(dllexport)
  #endif
#else
  #define MAGIC_EXPORT_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
}
#endif

# Changelog
All significant changes will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and adheres to [Semantic Versioning](https://semver.org/).

## [v1.2.3] - 2025-12-16

**Corresponding Core Firmware Version: >= MagicBot-Gen1 20251216**

### Added
- Added state estimation topic interface in the low-level motion mode;

## [v1.2.2-hotfix1] - 2025-12-11

**Corresponding Core Firmware Version: >= MagicBot-Gen1 20251128**

### Added
- Added SDK development documentation;

## [v1.2.2] - 2025-12-04

**Corresponding Core Firmware Version: >= MagicBot-Z1 20251118**

### Changed
- Optimize the issues present in the example.

## [v1.2.1] - 2025-11-21

**Corresponding Core Firmware Version: >= MagicBot-Z1 20251118**

### Changed
- Lidar point-cloud and camera image data are transmitted via ZMQ.
- Camera intrinsic parameters are transmitted via LCM, with the port number updated.

## [v1.2.0] - 2025-11-03

**Corresponding Core Firmware Version: >= MagicBot-Z1 20251101**

### Added
- Added SLAM mapping and navigation interfaces;

### Changed
- Added more SDK log outputs;
- Optimized underlying topic communication logic;
- Added timeout parameter to some RPC interfaces;
- Updated `example` samples;

### Deprecated
- Removed the global `SetTimeout` interface;

## [v1.0.0-hotfix1] - 2025-11-03

### Fixed
- Fixed occasional data loss in subscribe data subscription;

### Changed
- Updated README instructions

## [v1.0.0] - 2025-09-18

### Added
- Project initialization and establishment of base directory structure
- Implemented and uploaded core functional modules, supporting C++ and Python
- Added basic test samples
- Added basic files including README, LICENSE, .gitignore, etc.
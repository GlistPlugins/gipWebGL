# To build against a local assimp checkout instead of the pinned commit:
#   cmake -DFETCHCONTENT_SOURCE_DIR_ASSIMP=/path/to/assimp ...

include_guard(GLOBAL)

include(FetchContent)

# Extract with the download time as the timestamp, so a re-extract does not
# leave source files older than the build outputs made from them.
if(POLICY CMP0135)
	cmake_policy(SET CMP0135 NEW)
endif()

# The source archive is fetched instead of the repository. Cloning assimp from
# GitHub takes minutes, the archive takes seconds, and the checksum pins the
# contents just as tightly as a commit does.
#
# Both values move together when the version is bumped. The checksum comes from
# `sha256sum` of the same URL.
set(_assimp_commit "b41ffa556184b471912319a790d2fefc9f0c8fe2")
set(_assimp_sha256 "1f99e321587d0f3c7afb6e8c523e85d5be16aee5bba6219b01121568bee2bdcd")

# assimp asks for CMake 3.10, under which option() ignores a plain variable of
# the same name (CMP0077 OLD). Its options have to be set as cache entries.
#
# Tests and install rules are on by default. ASSIMP_INSTALL in particular would
# add assimp's install rules to the app; assimp's own description of the option
# says to turn it off when assimp is built as part of another project.
set(ASSIMP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(ASSIMP_BUILD_SAMPLES OFF CACHE BOOL "" FORCE)
set(ASSIMP_BUILD_ASSIMP_TOOLS OFF CACHE BOOL "" FORCE)
set(ASSIMP_INSTALL OFF CACHE BOOL "" FORCE)

# Also on by default, and what counts as a warning changes with every compiler
# release, so leaving it on makes the build break on toolchain upgrades.
set(ASSIMP_WARNINGS_AS_ERRORS OFF CACHE BOOL "" FORCE)

# There is no .git in an extracted archive, and without this assimp runs git in
# its source directory anyway, which reports whatever repository encloses the
# build directory.
set(ASSIMP_IGNORE_GIT_HASH ON CACHE BOOL "" FORCE)

FetchContent_Declare(assimp
		URL "https://github.com/assimp/assimp/archive/${_assimp_commit}.tar.gz"
		URL_HASH SHA256=${_assimp_sha256}
)
FetchContent_MakeAvailable(assimp)

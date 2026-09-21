# To build against a local freetype checkout instead of the pinned commit:
#   cmake -DFETCHCONTENT_SOURCE_DIR_FREETYPE=/path/to/freetype ...

include_guard(GLOBAL)

include(FetchContent)

# Extract with the download time as the timestamp, so a re-extract does not
# leave source files older than the build outputs made from them.
if(POLICY CMP0135)
	cmake_policy(SET CMP0135 NEW)
endif()

# Fetched the same way as assimp, see external/assimp.cmake.
#
# Both values move together when the version is bumped. The checksum comes from
# `sha256sum` of the same URL.
set(_freetype_commit "7955c9b86abfbce40ca7b06579bb1de8c945762f")
set(_freetype_sha256 "776690f553b251559217e072147e2c662c03f8b5166225882f94673149928226")

# freetype is built for the app to link against, not to be installed with it.
set(SKIP_INSTALL_ALL TRUE)

FetchContent_Declare(freetype
		URL "https://github.com/freetype/freetype/archive/${_freetype_commit}.tar.gz"
		URL_HASH SHA256=${_freetype_sha256}
)
FetchContent_MakeAvailable(freetype)

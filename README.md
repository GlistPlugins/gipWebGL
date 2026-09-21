# gipWebGL

This repository contains necessary WebGL libraries and sources for GlistEngine.

# Cloning

You should clone this repository under glistplugins (C:/dev/glist/glistplugins for Windows or ~/dev/glist/glistplugins for Linux and Mac) with `git clone https://github.com/glistplugins/gipWebGL` command.

# Dependencies

assimp and freetype are downloaded by CMake while configuring a web build, so a plain clone is all you need. Each one is pinned to a commit and its checksum in `external/assimp.cmake` and `external/freetype.cmake`.

To build against a local checkout instead of the pinned version, pass its path to CMake:

	-DFETCHCONTENT_SOURCE_DIR_ASSIMP=/path/to/assimp

Once a build directory has fetched them, `-DFETCHCONTENT_FULLY_DISCONNECTED=ON` keeps CMake from touching the network again.


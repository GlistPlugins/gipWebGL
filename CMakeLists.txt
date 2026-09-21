cmake_minimum_required (VERSION 3.10.2)

##### PLUGIN NAME #####
set(pluginname gipWebGL)

##### PLUGIN PATHS #####
set(PLUGIN_DIR ${PLUGINS_DIR}/${pluginname})
set(PLUGIN_LIBS_DIR ${PLUGIN_DIR}/libs)

if(EMSCRIPTEN)

##### DEPENDENCIES #####
# Fetched at configure time, see external/ for the pinned versions.
#
# Everything ends up in one wasm module, so the dependencies are built static.
# assimp would otherwise turn BUILD_SHARED_LIBS on for the whole build and leave
# the engine linking against a libassimp.so that the app cannot resolve.
#
# They are linked into the engine, which is a shared module, so they have to be
# position independent as well.
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
include(${PLUGIN_DIR}/external/assimp.cmake)
include(${PLUGIN_DIR}/external/freetype.cmake)

##### ENGINE DEFINES #####
# Emscripten only defines __EMSCRIPTEN__ these days, the engine sources still
# test the unprefixed name. Set after the dependencies so it stays off their
# builds.
add_compile_definitions(EMSCRIPTEN)

##### THREADS #####
# The engine links with -pthread, which asks wasm-ld for shared memory. Nothing
# is compiled with it and the web build is single threaded, so drop it.
list(REMOVE_ITEM GLIST_SHARED_LINKER_FLAGS -pthread)

list(APPEND PLUGIN_INCLUDES
		${PLUGIN_DIR}/src
		${PLUGIN_DIR}/include
		${freetype_SOURCE_DIR}/include
)

list(APPEND SRC_FILES
)

list(APPEND PLUGIN_SRCS
		${PLUGIN_DIR}/libs/sqlite3.c
		${PLUGIN_DIR}/src/gWebApp.cpp
		${PLUGIN_DIR}/src/gWebCanvas.cpp
		${ENGINE_DIR}/core/gGLFWWindow.cpp
)

list(APPEND PLUGIN_LINKLIBS
		assimp
		GL
		freetype
		glfw
)

if(CMAKE_HOST_SYSTEM_NAME STREQUAL "Linux")
	set(SHADERTOHEADER_EXEC_PATH "${PLUGIN_DIR}/tools/GlistShaderToHeader-linux-x86_64")
elseif(CMAKE_HOST_SYSTEM_NAME STREQUAL "Darwin")
	set(SHADERTOHEADER_EXEC_PATH "${PLUGIN_DIR}/tools/GlistShaderToHeader-macos-universal")
elseif(CMAKE_HOST_SYSTEM_NAME STREQUAL "Windows")
	set(SHADERTOHEADER_EXEC_PATH "${PLUGIN_DIR}/tools/GlistShaderToHeader-win-x86_64.exe")
endif()

endif()
cmake_minimum_required (VERSION 3.10.2)

##### PLUGIN NAME #####
set(pluginname gipWeb)


##### PLUGIN PATHS #####
set(PLUGIN_DIR ${PLUGINS_DIR}/${pluginname})
set(PLUGIN_LIBS_DIR ${PLUGIN_DIR}/libs)

set(CMAKE_TOOLCHAIN_FILE /opt/homebrew/opt/emscripten/libexec/cmake/Modules/Platform/Emscripten.cmake)

##### PLUGIN HEADERS #####
list(APPEND PLUGIN_INCLUDES
		${PLUGIN_DIR}/src
		${PLUGIN_DIR}/include
		${PLUGIN_DIR}/deps/freetype/include
)

list(APPEND SRC_FILES
)

##### PLUGIN SOURCES #####
list(APPEND PLUGIN_SRCS
		${PLUGIN_DIR}/libs/sqlite3.c
		${PLUGIN_DIR}/src/gWebApp.cpp
		${PLUGIN_DIR}/src/gWebCanvas.cpp
		${ENGINE_DIR}/core/gGLFWWindow.cpp
)

set(ASSIMP_BUILD_TESTS OFF)
set(ASSIMP_WARNINGS_AS_ERRORS OFF)
add_subdirectory(${PLUGIN_DIR}/deps/assimp ${CMAKE_BINARY_DIR}/assimp EXCLUDE_FROM_ALL)
set(FT_DISABLE_HARFBUZZ ON)
add_subdirectory(${PLUGIN_DIR}/deps/freetype ${CMAKE_BINARY_DIR}/freetype EXCLUDE_FROM_ALL)


list(APPEND PLUGIN_LINKLIBS
		assimp
		GL
		freetype
		glfw
)

list(APPEND GLIST_SHARED_LINKER_FLAGS "-s FULL_ES=1 -s USE_WEBGL2=1 USE_GLFW=3 USE_FREETYPE=1 USE_SQLITE=1 -s USE_FREETYPE=1 -s USE_LIBPNG=1 -s USE_ZLIB=1 -s USE_SQLITE=1 -s USE_HARFBUZZ=1")

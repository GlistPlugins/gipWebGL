cmake_minimum_required (VERSION 3.10.2)

##### PLUGIN NAME #####
set(pluginname gipWebGL)

##### PLUGIN PATHS #####
set(PLUGIN_DIR ${PLUGINS_DIR}/${pluginname})
set(PLUGIN_LIBS_DIR ${PLUGIN_DIR}/libs)

if(EMSCRIPTEN)

list(APPEND PLUGIN_INCLUDES
		${PLUGIN_DIR}/src
		${PLUGIN_DIR}/include
		${PLUGIN_DIR}/deps/freetype/include
)

list(APPEND SRC_FILES
)

list(APPEND PLUGIN_SRCS
		${PLUGIN_DIR}/libs/sqlite3.c
		${PLUGIN_DIR}/src/gWebApp.cpp
		${PLUGIN_DIR}/src/gWebCanvas.cpp
		${ENGINE_DIR}/core/gGLFWWindow.cpp
)

add_subdirectory(${PLUGIN_DIR}/deps/assimp ${CMAKE_BINARY_DIR}/assimp EXCLUDE_FROM_ALL)
add_subdirectory(${PLUGIN_DIR}/deps/freetype ${CMAKE_BINARY_DIR}/freetype EXCLUDE_FROM_ALL)


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
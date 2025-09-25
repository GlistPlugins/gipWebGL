#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path
import platform

import json

def copy_assets(project_path, build_dir):
    """Copy assets to build directory for Emscripten to pack."""
    assets_dir = project_path / "assets"
    if not assets_dir.exists():
        print("No assets directory found, skipping asset copying")
        return None

    # Copy assets to build directory so Emscripten can find them
    build_assets_dir = build_dir / "assets"
    if build_assets_dir.exists():
        shutil.rmtree(build_assets_dir)

    try:
        shutil.copytree(assets_dir, build_assets_dir)
        print(f"Assets copied to: {build_assets_dir}")
        return build_assets_dir
    except Exception as e:
        print(f"ERROR: Failed to copy assets: {e}")
        return None

def find_cmake_executable():
    """Find cmake executable in system PATH or glist zbin directory."""
    # First try system PATH
    try:
        subprocess.run(["cmake", "--version"], check=True, capture_output=True)
        print("Using cmake from system PATH")
        return "cmake"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try to find in glist zbin directory
    current_dir = Path.cwd()
    glist_dir = current_dir.parent.parent  # gipWebGL -> glistplugins -> glist
    zbin_dir = glist_dir / "zbin"

    if zbin_dir.exists():
        # Look for glistzbin-* directories
        for zbin_platform_dir in zbin_dir.glob("glistzbin-*"):
            if zbin_platform_dir.is_dir():
                # Try different possible cmake paths
                cmake_paths = [
                    zbin_platform_dir / "cmake" / "bin" / "cmake",
                    zbin_platform_dir / "cmake" / "bin" / "cmake.exe",
                    zbin_platform_dir / "CMake" / "bin" / "cmake",
                    zbin_platform_dir / "CMake" / "bin" / "cmake.exe",
                    zbin_platform_dir / "bin" / "cmake",
                    zbin_platform_dir / "bin" / "cmake.exe"
                ]

                for cmake_path in cmake_paths:
                    if cmake_path.exists():
                        print(f"Found cmake at: {cmake_path}")
                        return str(cmake_path)

    print("ERROR: Could not find cmake executable")
    return None


def setup_emscripten_cmake_flags(project_path, build_dir):
    """Setup Emscripten-specific CMake flags for asset loading and web output."""
    flags = []

    # Check if assets directory exists
    assets_dir = build_dir / "assets"
    if assets_dir.exists() and any(assets_dir.iterdir()):
        # Use Emscripten's --preload-file to pack assets
        flags.extend([
            f"-DCMAKE_EXE_LINKER_FLAGS=--preload-file {assets_dir}@/assets"
        ])
        print("Assets found - will be packed with --preload-file")

    # Add common Emscripten web optimization flags
    common_flags = [
        "-DCMAKE_EXECUTABLE_SUFFIX=\".html\"",
        "-DCMAKE_EXE_LINKER_FLAGS_RELEASE=-s EXPORTED_FUNCTIONS=['_main','_malloc','_free'] -s EXPORTED_RUNTIME_METHODS=['ccall','cwrap']"
    ]

    flags.extend(common_flags)
    return flags


def compile_project(project_path):
    """Compile the selected project using emscripten with native asset packing."""
    project_name = project_path.name
    build_dir = Path("./build").absolute() / project_name

    # Create build directory
    build_dir.mkdir(parents=True, exist_ok=True)

    # Clear CMake cache to avoid generator conflicts
    cmake_cache = build_dir / "CMakeCache.txt"
    cmake_files_dir = build_dir / "CMakeFiles"

    if cmake_cache.exists():
        print("Clearing CMake cache...")
        cmake_cache.unlink()

    if cmake_files_dir.exists():
        print("Clearing CMakeFiles directory...")
        shutil.rmtree(cmake_files_dir)

    # Copy assets for Emscripten to pack
    copy_assets(project_path, build_dir)

    # Setup emscripten environment
    setup_emscripten_env()

    # Find cmake executable
    cmake_cmd = find_cmake_executable()
    if not cmake_cmd:
        return False

    # Find build tool (ninja or make)
    build_cmd, generator = find_or_install_ninja()
    if not build_cmd:
        return False

    try:
        # Find emscripten toolchain file
        emsdk_dir = Path("./emsdk").absolute()
        if emsdk_dir.exists():
            toolchain_file = emsdk_dir / "upstream" / "emscripten" / "cmake" / "Modules" / "Platform" / "Emscripten.cmake"
        else:
            # Try to find in system
            result = subprocess.run(["emcc", "--print-sysroot"], capture_output=True, text=True)
            if result.returncode == 0:
                sysroot = result.stdout.strip()
                toolchain_file = Path(sysroot).parent / "cmake" / "Modules" / "Platform" / "Emscripten.cmake"
            else:
                print("ERROR: Could not find emscripten toolchain file")
                return False

        print(f"Using toolchain file: {toolchain_file}")
        print(f"Using cmake: {cmake_cmd}")
        print(f"Using build tool: {build_cmd} (generator: {generator})")

        # Get Emscripten-specific flags
        emscripten_flags = setup_emscripten_cmake_flags(project_path, build_dir)

        # Configure with CMake
        cmake_args = [
            cmake_cmd,
            "-DCMAKE_TOOLCHAIN_FILE=" + str(toolchain_file),
            "-DCMAKE_BUILD_TYPE=Release",

            # Use the appropriate build tool
            "-DCMAKE_MAKE_PROGRAM=" + build_cmd,
            "-G", generator,

            # Emscripten-specific fixes
            "-DCMAKE_CROSSCOMPILING=ON",
            "-DCMAKE_SYSTEM_NAME=Emscripten",
            "-DCMAKE_SYSTEM_PROCESSOR=x86",

            # Fix for CheckTypeSize issues with Emscripten
            "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY",

            # Assimp configuration
            "-DASSIMP_BUILD_ZLIB=ON",
            "-DASSIMP_WARNINGS_AS_ERRORS=OFF",

            # FreeType configuration
            "-DFT_DISABLE_HARFBUZZ=ON",

            # General dependency management
            "-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER",
            "-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY",
            "-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY",

            # Skip problematic checks
            "-DHAVE_OFF64_T=OFF",
            "-DOFF64_T=OFF",

            "-B", str(build_dir),
            "-S", str(project_path)
        ]

        # Add Emscripten-specific flags
        cmake_args.extend(emscripten_flags)

        print("Configuring project...")
        print(f"Running: {' '.join(cmake_args)}")
        result = subprocess.run(cmake_args)
        if result.returncode != 0:
            print("ERROR: CMake configuration failed")
            return False

        # Build project
        print("Building project...")
        build_args = [cmake_cmd, "--build", str(build_dir)]
        print(f"Running: {' '.join(build_args)}")
        result = subprocess.run(build_args)
        if result.returncode != 0:
            print("ERROR: Build failed")
            return False

        print(f"Project built successfully in {build_dir}")
        return True

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        print(f"ERROR: Compilation failed: {e}")
        return False


def create_zip_package(project_path):
    """Create a zip file with only the Emscripten-generated web files."""
    project_name = project_path.name
    build_dir = Path("./build") / project_name
    zip_path = Path("./build") / f"{project_name}_webgl.zip"

    if not build_dir.exists():
        print("ERROR: Build directory does not exist")
        return False

    try:
        # Emscripten generates these files for web deployment
        expected_files = [
            f"{project_name}.html",  # Main HTML file
            f"{project_name}.js",  # JavaScript loader
            f"{project_name}.wasm",  # WebAssembly binary
            f"{project_name}.data"  # Asset data file (if assets exist)
        ]

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files_added = []

            # Add Emscripten-generated files
            for filename in expected_files:
                file_path = build_dir / filename
                if file_path.exists():
                    zipf.write(file_path, filename)
                    files_added.append(filename)
                    print(f"Added: {filename}")
                else:
                    print(f"Note: {filename} not found (may not be needed)")

            # Look for any other web-compatible files that might have been generated
            web_extensions = {'.html', '.js', '.wasm', '.data', '.map'}
            for file_path in build_dir.rglob('*'):
                if (file_path.is_file() and
                        file_path.suffix.lower() in web_extensions and
                        file_path.name not in files_added and
                        not file_path.name.startswith('.')):
                    zipf.write(file_path, file_path.name)
                    files_added.append(file_path.name)
                    print(f"Added additional file: {file_path.name}")

            # Create a deployment README
            readme_content = f"""WebGL Deployment Package for {project_name}
{'=' * (30 + len(project_name))}

This package contains the Emscripten-compiled WebGL version of your project.

DEPLOYMENT:
1. Extract all files to your web server directory
2. Access {project_name}.html through a web server (NOT file://)

SIMPLE LOCAL WEB SERVER:
- Python: python -m http.server 8000
- Node.js: npx serve .
- PHP: php -S localhost:8000

Generated by Emscripten:
{chr(10).join(f'- {file}' for file in sorted(files_added))}

The .data file (if present) contains your packed assets.
The .wasm file contains your compiled application code.
The .js file handles WebAssembly loading and browser integration.
"""

            zipf.writestr("README.txt", readme_content)

        # Show summary
        zip_size = zip_path.stat().st_size
        print(f"\nPackage created: {zip_path}")
        print(f"Files: {len(files_added)} + README.txt")
        print(f"Size: {zip_size / 1024:.1f} KB")

        return True

    except Exception as e:
        print(f"ERROR: Failed to create zip package: {e}")
        return False

def create_asset_pack(project_path, build_dir):
    """Create an asset pack file containing all assets."""
    assets_dir = project_path / "assets"
    if not assets_dir.exists():
        print("No assets directory found, skipping asset pack creation")
        return None
    
    asset_pack = {}
    asset_pack_path = build_dir / "assets.pak"
    
    try:
        # Collect all asset files
        for asset_file in assets_dir.rglob('*'):
            if asset_file.is_file():
                relative_path = asset_file.relative_to(assets_dir)
                
                # Read file as binary
                with open(asset_file, 'rb') as f:
                    file_data = f.read()
                
                # Store as base64 for JSON serialization
                import base64
                asset_pack[str(relative_path)] = {
                    'data': base64.b64encode(file_data).decode('utf-8'),
                    'size': len(file_data),
                    'type': asset_file.suffix.lower()
                }
        
        # Write asset pack file
        with open(asset_pack_path, 'w') as f:
            json.dump(asset_pack, f, separators=(',', ':'))
        
        print(f"Asset pack created: {asset_pack_path} ({len(asset_pack)} files)")
        return asset_pack_path
        
    except Exception as e:
        print(f"ERROR: Failed to create asset pack: {e}")
        return None

def check_folder_structure():
    """Check if the current directory structure is correct."""
    current_dir = Path.cwd()
    
    # Check current directory name
    if current_dir.name != "gipWebGL":
        print("ERROR: Current directory must be named 'gipWebGL'")
        return False
    
    # Check parent directory structure
    parent = current_dir.parent
    if parent.name != "glistplugins":
        print("ERROR: Parent directory must be named 'glistplugins'")
        return False
    
    glist_dir = parent.parent
    if glist_dir.name != "glist":
        print("ERROR: Parent of glistplugins must be named 'glist'")
        return False
    
    dev_dir = glist_dir.parent
    if dev_dir.name != "dev":
        print("ERROR: Parent of glist must be named 'dev'")
        return False
    
    # Check required directories in glist folder
    glistengine_dir = glist_dir / "glistengine"
    myglistapps_dir = glist_dir / "myglistapps"
    
    if not glistengine_dir.exists():
        print("ERROR: 'glistengine' directory not found in glist folder")
        return False
    
    if not myglistapps_dir.exists():
        print("ERROR: 'myglistapps' directory not found in glist folder")
        return False
    
    print("Folder structure validation: PASSED")
    return True

def check_and_install_emsdk():
    """Check if emsdk is available and install if needed."""
    # Check if emcc is available in PATH
    try:
        subprocess.run(["emcc", "--version"], check=True, capture_output=True)
        print("Emscripten found in PATH")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Check if emsdk exists locally
    emsdk_dir = Path("./emsdk")
    if emsdk_dir.exists():
        # Try to activate emsdk
        try:
            if os.name == 'nt':  # Windows
                activate_script = emsdk_dir / "emsdk_env.bat"
                if activate_script.exists():
                    print("Local emsdk found")
                    return True
            else:  # Unix-like
                activate_script = emsdk_dir / "emsdk_env.sh"
                if activate_script.exists():
                    print("Local emsdk found")
                    return True
        except Exception as e:
            print(f"Error checking local emsdk: {e}")
    
    # Install emsdk
    print("Installing emsdk...")
    try:
        # Clone emsdk
        subprocess.run([
            "git", "clone", "https://github.com/emscripten-core/emsdk.git", "./emsdk"
        ], check=True)
        
        # Install and activate latest
        emsdk_path = "./emsdk/emsdk"
        if os.name == 'nt':  # Windows
            emsdk_path += ".bat"
        
        subprocess.run([emsdk_path, "install", "latest"], check=True)
        subprocess.run([emsdk_path, "activate", "latest"], check=True)
        
        print("Emscripten SDK installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install emsdk: {e}")
        return False

def find_cmake_projects():
    """Find all directories with CMakeLists.txt under myglistapps."""
    current_dir = Path.cwd()
    glist_dir = current_dir.parent.parent
    myglistapps_dir = glist_dir / "myglistapps"
    
    if os.name == 'nt':  # Windows
        myglistapps_path = Path("C:/dev/glist/myglistapps")
    else:
        myglistapps_path = myglistapps_dir
    
    projects = []
    
    if not myglistapps_path.exists():
        print(f"ERROR: {myglistapps_path} does not exist")
        return projects
    
    # Only list direct subdirectories (not recursive)
    for item in myglistapps_path.iterdir():
        if item.is_dir():
            cmake_file = item / "CMakeLists.txt"
            if cmake_file.exists():
                projects.append(item)
    
    return projects

def select_project(projects):
    """Let user select a project from the list."""
    if not projects:
        print("No projects with CMakeLists.txt found")
        return None
    
    print("\nAvailable projects:")
    for i, project in enumerate(projects, 1):
        print(f"{i}. {project.name}")
    
    while True:
        try:
            choice = input(f"\nSelect a project (1-{len(projects)}): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(projects):
                return projects[index]
            else:
                print(f"Please enter a number between 1 and {len(projects)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return None

def find_or_install_ninja():
    """Find ninja executable in system PATH, glist zbin, or install it."""

    # First try system PATH
    try:
        subprocess.run(["ninja", "--version"], check=True, capture_output=True)
        print("Using ninja from PATH ")
        return Path(shutil.which("ninja")).absolute().__str__(), "Ninja"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try to find in glist zbin directory
    current_dir = Path.cwd()
    glist_dir = current_dir.parent.parent  # gipWebGL -> glistplugins -> glist
    zbin_dir = glist_dir / "zbin"
    
    if zbin_dir.exists():
        # Look for glistzbin-* directories
        for zbin_platform_dir in zbin_dir.glob("glistzbin-*"):
            if zbin_platform_dir.is_dir():
                # Try different possible ninja paths
                ninja_paths = [
                    zbin_platform_dir / "bin" / "ninja.exe",
                    zbin_platform_dir / "bin" / "ninja",
                    zbin_platform_dir / "clang64" / "bin" / "ninja.exe",
                    zbin_platform_dir / "clang64" / "bin" / "ninja"
                ]
                
                for ninja_path in ninja_paths:
                    if ninja_path.exists():
                        print(f"Found ninja at: {ninja_path}")
                        # Add the bin directory to PATH
                        bin_dir = ninja_path.parent
                        current_path = os.environ.get('PATH', '')
                        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{current_path}"
                        return str(ninja_path), "Ninja"
    
    # Check if ninja is already installed locally
    local_ninja = Path("./ninja").absolute()
    if os.name == 'nt':
        local_ninja = Path("./ninja.exe").absolute()
    
    if local_ninja.exists():
        print(f"Using local ninja: {local_ninja}")
        # Make sure it's executable on Unix systems
        if os.name != 'nt':
            local_ninja.chmod(0o755)
        
        # Add current directory to PATH so ninja can be found by cmake
        current_dir_str = str(Path.cwd().absolute())
        current_path = os.environ.get('PATH', '')
        if current_dir_str not in current_path:
            os.environ["PATH"] = f"{current_dir_str}{os.pathsep}{current_path}"
        
        # Test that ninja actually works
        try:
            ninja_cmd = "ninja.exe" if os.name == 'nt' else "ninja"
            result = subprocess.run([ninja_cmd, "--version"], check=True, capture_output=True, text=True)
            print(f"Local ninja version: {result.stdout.strip()}")
            return str(local_ninja), "Ninja"
        except Exception as e:
            print(f"Local ninja found but not working: {e}")
            # Continue to installation
    
    # Install ninja based on platform
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    print(f"Ninja not found, installing for {system} {machine}...")
    
    try:
        if system == "windows":
            return install_ninja_windows()
        elif system == "linux":
            return install_ninja_linux()
        elif system == "darwin":  # macOS
            return install_ninja_macos()
        else:
            print(f"Unsupported platform: {system}")
            return fallback_to_make()
    except Exception as e:
        print(f"Failed to install ninja: {e}")
        return fallback_to_make()

def install_ninja_windows():
    """Install ninja on Windows by downloading from GitHub releases."""
    import urllib.request
    import zipfile
    
    ninja_url = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-win.zip"
    ninja_zip = Path("./ninja-win.zip")
    
    print("Downloading ninja for Windows...")
    urllib.request.urlretrieve(ninja_url, ninja_zip)
    
    print("Extracting ninja...")
    with zipfile.ZipFile(ninja_zip, 'r') as zip_ref:
        zip_ref.extractall(".")
    
    ninja_zip.unlink()  # Delete the zip file
    
    ninja_exe = Path("./ninja.exe").absolute()
    if ninja_exe.exists():
        # Add current directory to PATH
        current_dir_str = str(Path.cwd().absolute())
        current_path = os.environ.get('PATH', '')
        if current_dir_str not in current_path:
            os.environ["PATH"] = f"{current_dir_str}{os.pathsep}{current_path}"
        
        # Test that ninja works
        try:
            result = subprocess.run(["ninja.exe", "--version"], check=True, capture_output=True, text=True)
            print(f"Ninja installed successfully. Version: {result.stdout.strip()}")
            return str(ninja_exe), "Ninja"
        except Exception as e:
            print(f"Ninja executable found but not working: {e}")
            raise Exception("Ninja installation verification failed")
    else:
        raise Exception("Ninja extraction failed")

def install_ninja_linux():
    """Install ninja on Linux using package manager."""
    # Try different package managers
    package_managers = [
        (["apt-get", "update"], ["apt-get", "install", "-y", "ninja-build"]),
        (["yum", "update"], ["yum", "install", "-y", "ninja-build"]),
        (["dnf", "update"], ["dnf", "install", "-y", "ninja-build"]),
        (["pacman", "-Sy"], ["pacman", "-S", "--noconfirm", "ninja"]),
        (["zypper", "refresh"], ["zypper", "install", "-y", "ninja"]),
    ]
    
    for update_cmd, install_cmd in package_managers:
        try:
            print(f"Trying package manager: {install_cmd[0]}")
            subprocess.run(update_cmd, check=True, capture_output=True)
            subprocess.run(install_cmd, check=True, capture_output=True)
            
            # Verify installation
            subprocess.run(["ninja", "--version"], check=True, capture_output=True)
            print("Ninja installed successfully via package manager")
            return "ninja", "Ninja"
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    # If package managers fail, try downloading binary
    return download_ninja_binary_linux()

def download_ninja_binary_linux():
    """Download ninja binary for Linux."""
    import urllib.request
    import zipfile
    
    ninja_url = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-linux.zip"
    ninja_zip = Path("./ninja-linux.zip")
    
    print("Downloading ninja binary for Linux...")
    urllib.request.urlretrieve(ninja_url, ninja_zip)
    
    print("Extracting ninja...")
    with zipfile.ZipFile(ninja_zip, 'r') as zip_ref:
        zip_ref.extractall(".")
    
    ninja_zip.unlink()  # Delete the zip file
    
    ninja_bin = Path("./ninja").absolute()
    if ninja_bin.exists():
        # Make executable
        ninja_bin.chmod(0o755)
        
        # Add current directory to PATH
        current_dir_str = str(Path.cwd().absolute())
        current_path = os.environ.get('PATH', '')
        if current_dir_str not in current_path:
            os.environ["PATH"] = f"{current_dir_str}{os.pathsep}{current_path}"
        
        # Test that ninja works
        try:
            result = subprocess.run(["ninja", "--version"], check=True, capture_output=True, text=True)
            print(f"Ninja installed successfully. Version: {result.stdout.strip()}")
            return str(ninja_bin), "Ninja"
        except Exception as e:
            print(f"Ninja executable found but not working: {e}")
            raise Exception("Ninja installation verification failed")
    else:
        raise Exception("Ninja extraction failed")

def install_ninja_macos():
    """Install ninja on macOS using Homebrew."""
    try:
        # Try Homebrew first
        print("Trying to install ninja via Homebrew...")
        subprocess.run(["brew", "install", "ninja"], check=True)
        
        # Verify installation
        subprocess.run(["ninja", "--version"], check=True, capture_output=True)
        print("Ninja installed successfully via Homebrew")
        return "ninja", "Ninja"
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Homebrew not found or failed, trying direct download...")
        return download_ninja_binary_macos()

def download_ninja_binary_macos():
    """Download ninja binary for macOS."""
    import urllib.request
    import zipfile
    
    ninja_url = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-mac.zip"
    ninja_zip = Path("./ninja-mac.zip")
    
    print("Downloading ninja binary for macOS...")
    urllib.request.urlretrieve(ninja_url, ninja_zip)
    
    print("Extracting ninja...")
    with zipfile.ZipFile(ninja_zip, 'r') as zip_ref:
        zip_ref.extractall(".")
    
    ninja_zip.unlink()  # Delete the zip file
    
    ninja_bin = Path("./ninja").absolute()
    if ninja_bin.exists():
        # Make executable
        ninja_bin.chmod(0o755)
        
        # Add current directory to PATH
        current_dir_str = str(Path.cwd().absolute())
        current_path = os.environ.get('PATH', '')
        if current_dir_str not in current_path:
            os.environ["PATH"] = f"{current_dir_str}{os.pathsep}{current_path}"
        
        # Test that ninja works
        try:
            result = subprocess.run(["ninja", "--version"], check=True, capture_output=True, text=True)
            print(f"Ninja installed successfully. Version: {result.stdout.strip()}")
            return str(ninja_bin), "Ninja"
        except Exception as e:
            print(f"Ninja executable found but not working: {e}")
            raise Exception("Ninja installation verification failed")
    else:
        raise Exception("Ninja extraction failed")

def fallback_to_make():
    """Fallback to make if ninja installation fails."""
    print("Falling back to make...")
    
    # First try to find in glist zbin directory
    current_dir = Path.cwd()
    glist_dir = current_dir.parent.parent  # gipWebGL -> glistplugins -> glist
    zbin_dir = glist_dir / "zbin"
    
    if zbin_dir.exists():
        # Look for glistzbin-* directories
        for zbin_platform_dir in zbin_dir.glob("glistzbin-*"):
            if zbin_platform_dir.is_dir():
                # Try different possible make paths
                make_paths = [
                    zbin_platform_dir / "clang64" / "bin" / "mingw32-make.exe",
                    zbin_platform_dir / "clang64" / "bin" / "make.exe",
                    zbin_platform_dir / "bin" / "mingw32-make.exe",
                    zbin_platform_dir / "bin" / "make.exe",
                    zbin_platform_dir / "bin" / "make"
                ]
                
                for make_path in make_paths:
                    if make_path.exists():
                        print(f"Found make at: {make_path}")
                        # Add the bin directory to PATH
                        bin_dir = make_path.parent
                        current_path = os.environ.get('PATH', '')
                        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{current_path}"
                        return str(make_path), "Unix Makefiles"
    
    # Fall back to system PATH
    try:
        subprocess.run(["make", "--version"], check=True, capture_output=True)
        print("Using make from system PATH")
        return "make", "Unix Makefiles"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Try mingw32-make in system PATH
    try:
        subprocess.run(["mingw32-make", "--version"], check=True, capture_output=True)
        print("Using mingw32-make from system PATH")
        return "mingw32-make", "Unix Makefiles"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    print("ERROR: Could not find make executable")
    return None, None

def setup_emscripten_env():
    """Setup emscripten environment variables."""
    emsdk_dir = Path("./emsdk").absolute()
    if emsdk_dir.exists():
        # For local emsdk, we need to source the environment
        upstream_emscripten = emsdk_dir / "upstream" / "emscripten"
        
        os.environ["EMSDK"] = str(emsdk_dir)
        os.environ["EM_CONFIG"] = str(emsdk_dir / ".emscripten")
        
        # Add emscripten to PATH at the beginning
        current_path = os.environ.get('PATH', '')
        os.environ["PATH"] = f"{upstream_emscripten}{os.pathsep}{current_path}"
        
        # Set emscripten-specific variables
        os.environ["EMSCRIPTEN"] = str(upstream_emscripten)
        
        print(f"Emscripten environment configured: {upstream_emscripten}")
        
        # Verify emcc is accessible
        try:
            emcc_path = upstream_emscripten / "emcc"
            if os.name == 'nt':
                # On Windows, try both emcc.bat and emcc
                emcc_candidates = [
                    upstream_emscripten / "emcc.bat",
                    upstream_emscripten / "emcc"
                ]
                for candidate in emcc_candidates:
                    if candidate.exists():
                        emcc_path = candidate
                        break
            
            result = subprocess.run([str(emcc_path), "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("Emscripten compiler verification: OK")
            else:
                print("WARNING: Emscripten compiler verification failed")
        except Exception as e:
            print(f"WARNING: Could not verify emscripten compiler: {e}")
    else:
        # Try to use system emscripten
        print("Using system emscripten (not found locally)")
        try:
            result = subprocess.run(["emcc", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("System emscripten verification: OK")
            else:
                print("WARNING: System emscripten verification failed")
        except Exception as e:
            print(f"WARNING: Could not verify system emscripten: {e}")

def main():
    """Main function."""
    print("GList WebGL Project Builder")
    print("=" * 40)
    
    # Check folder structure
    if not check_folder_structure():
        sys.exit(1)
    
    # Check and install emsdk
    if not check_and_install_emsdk():
        sys.exit(1)
    
    # Find cmake projects
    projects = find_cmake_projects()
    if not projects:
        print("No projects found")
        sys.exit(1)
    
    # Select project
    selected_project = select_project(projects)
    if not selected_project:
        sys.exit(1)
    
    print(f"\nSelected project: {selected_project.name}")
    
    # Compile project
    if not compile_project(selected_project):
        sys.exit(1)
    
    # Create zip package
    if not create_zip_package(selected_project):
        sys.exit(1)
    
    print("\nBuild completed successfully!")

if __name__ == "__main__":
    main()
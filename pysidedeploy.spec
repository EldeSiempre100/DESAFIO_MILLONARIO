[app]

# title of your application
title = Millonario Educativo V2

# project root directory. default = The parent directory of input_file
project_dir = .

# source file entry point path. default = main.py
input_file = main.py

# directory where the executable output is generated
exec_directory = dist

# path to the project file relative to project_dir
project_file = pyproject.toml

# application icon
icon = assets\icons\millonario.ico

[python]

# python path
python_path = C:\Users\Sysmark-IP1\Desktop\QUIEN_QUIERE_SER_\.venv\Scripts\python.exe

# python packages to install
packages = Nuitka==4.0

# buildozer = for deploying Android application
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]

# paths to required qml files. comma separated
# normally all the qml files required by the project are added automatically
# design studio projects include the qml files using qt resources
qml_files = qml\Main.qml

# excluded qml plugin binaries
excluded_qml_plugins = Qt3D,Qt5Compat,QtCharts,QtDataVisualization,QtGraphs,QtLocation,QtPositioning,QtQuick3D,QtSensors,QtTest,QtTextToSpeech,QtWebChannel,QtWebEngine,QtWebSockets,QtWebView

# qt modules used. comma separated
modules = Core,Gui,Multimedia,Qml,Quick,QuickControls2

# qt plugins used by the application. only relevant for desktop deployment
# for qt plugins used in android application see [android][plugins]
plugins = iconengines,imageformats,multimedia,platforminputcontexts,platforms,styles,tls

[android]

# path to pyside wheel
wheel_pyside =

# path to shiboken wheel
wheel_shiboken =

# plugins to be copied to libs folder of the packaged application. comma separated
plugins =

[nuitka]

# usage description for permissions requested by the app as found in the info.plist file
# of the app bundle. comma separated
# eg = extra_args = --show-modules --follow-stdlib
macos.permissions =

# mode of using nuitka. accepts standalone or onefile. default = onefile
mode = standalone

# specify any extra nuitka arguments
extra_args = --quiet --noinclude-qt-translations --include-data-dir=qml=qml --include-data-dir=assets=assets --include-data-dir=templates=templates --include-data-files=projects/demo.juego=projects/demo.juego --output-filename=MillonarioEducativo.exe --windows-console-mode=disable --company-name="Proyecto educativo privado" --product-name="Millonario educativo" --file-description="Juego audiovisual editable V2" --file-version=2.0.0.0 --product-version=2.0.0.0

[buildozer]

# build mode
# possible values = ["aarch64", "armv7a", "i686", "x86_64"]
# release creates a .aab, while debug creates a .apk
mode = debug

# path to pyside6 and shiboken6 recipe dir
recipe_dir =

# path to extra qt android .jar files to be loaded by the application
jars_dir =

# if empty, uses default ndk path downloaded by buildozer
ndk_path =

# if empty, uses default sdk path downloaded by buildozer
sdk_path =

# other libraries to be loaded at app startup. comma separated.
local_libs =

# architecture of deployed platform
arch =

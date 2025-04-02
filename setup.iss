[Setup]
AppName=简易翻译器
AppVersion=1.0
DefaultDirName={autopf}\简易翻译器
DefaultGroupName=简易翻译器
OutputBaseFilename=简易翻译器_安装程序
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\简易翻译器\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\简易翻译器"; Filename: "{app}\简易翻译器.exe"
Name: "{commondesktop}\简易翻译器"; Filename: "{app}\简易翻译器.exe"
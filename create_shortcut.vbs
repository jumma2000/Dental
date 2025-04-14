Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\ابتسامة المشاهير.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = oWS.CurrentDirectory & "\start_dental_clinic.bat"
oLink.WorkingDirectory = oWS.CurrentDirectory
oLink.IconLocation = "%SystemRoot%\System32\SHELL32.dll, 13"
oLink.Description = "نظام إدارة عيادة ابتسامة المشاهير لتجميل الاسنان"
oLink.Save

WScript.Echo "تم إنشاء اختصار على سطح المكتب بنجاح!"

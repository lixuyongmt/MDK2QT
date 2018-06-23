#coding: utf-8
''' 升级记录
2017/2/26
self.mdkproj['Defines'] = defines.split() if defines else []
更改为
self.mdkproj['Defines'] = defines.replace(',', ' ').split() if defines else []
因为MDK项目设置中定义的宏即可以空格分割，也可以逗号分割

2017/3/5
f.write(self.mdkproj['Groups'][group][path].replace('\\', '/') + '\n')
更改为
f.write(self.mdkproj['Groups'][group][path].replace('\\', '/').encode('gbk') + '\n')
因为MDK项目中文件若有中文名称则会导致写入编码错误
'''
import sys, os
import shutil
import uuid
import ConfigParser
import _winreg

import xml.etree.ElementTree as et

import sip
sip.setapi('QString', 2)
from PyQt4 import QtCore, QtGui, uic

'''
from MDK2QT_UI import Ui_MDK2QT
class MDK2QT(QtGui.QWidget, Ui_MDK2QT):
    def __init__(self, parent=None):
        super(MDK2QT, self).__init__(parent)
        
        self.setupUi(self)
'''
class MDK2QT(QtGui.QWidget):
    def __init__(self, parent=None):
        super(MDK2QT, self).__init__(parent)
        
        uic.loadUi('MDK2QT.ui', self)

        self.initSetting()
        
    def initSetting(self):
        if not os.path.exists('setting.ini'):
            open('setting.ini', 'w')
        
        self.conf = ConfigParser.ConfigParser()
        self.conf.read('setting.ini')
        
        if not self.conf.has_section('globals'):
            self.conf.add_section('globals')
            self.conf.set('globals', 'QT Version', 'QT 5.7')
            self.conf.set('globals', 'MDK Version', 'Keil MDK 4')
            self.conf.set('globals', 'MDK Projects', '[]')
        self.cmbQTVer.setCurrentIndex(self.cmbQTVer.findText(self.conf.get('globals', 'QT Version')))
        self.cmbMDKVer.setCurrentIndex(self.cmbMDKVer.findText(self.conf.get('globals', 'MDK Version')))
        for mdkpath in eval(self.conf.get('globals', 'MDK Projects').decode('gbk')): self.cmbMDKPrj.insertItem(10, mdkpath)
    
    @QtCore.pyqtSlot()
    def on_btnMDKPrj_clicked(self):
        mdkpath = QtGui.QFileDialog.getOpenFileName(self, caption=u'指定MDK项目文件', directory=self.cmbMDKPrj.currentText(),
                    filter='MDK 4 Project (*.uvproj)' if self.cmbMDKVer.currentText() == 'Keil MDK 4' else 'MDK 5 Project (*.uvprojx)')
        if mdkpath:
            self.cmbMDKPrj.insertItem(0, mdkpath)
            self.cmbMDKPrj.setCurrentIndex(0)
    
    @QtCore.pyqtSlot()
    def on_btnMake_clicked(self):
        self.btnMake.setEnabled(False)
        
        mdkpath = self.cmbMDKPrj.currentText()
        
        mdkname = os.path.basename(mdkpath)        
        self.mdkproj = {'mdkname': mdkname[:mdkname.rindex('.')]}
        
        self.parse_mdkproj(mdkpath)
        
        mdkpath = mdkpath[:mdkpath.rindex('.')]     #去掉后缀
        
        if self.cmbQTVer.currentText().endswith('Import'):
            shutil.copy(self.cmbQTVer.currentText()+r'\Template.creator',      mdkpath+'.creator')
            #shutil.copy(self.cmbQTVer.currentText()+r'\Template.creator.user', mdkpath+'.creator.user')
            shutil.copy(self.cmbQTVer.currentText()+r'\Template.files',        mdkpath+'.files')
            shutil.copy(self.cmbQTVer.currentText()+r'\Template.config',       mdkpath+'.config')
            shutil.copy(self.cmbQTVer.currentText()+r'\Template.includes',     mdkpath+'.includes')

            self.modify_all(mdkpath+'.files', mdkpath+'.config', mdkpath+'.includes')
        else:
            shutil.copy(self.cmbQTVer.currentText()+r'\Template.pro',      mdkpath+'.pro')
            #shutil.copy(self.cmbQTVer.currentText()+r'\Template.pro.user', mdkpath+'.pro.user')
            
            self.modify_pro(     mdkpath+'.pro')
            #self.modify_pro_user(mdkpath+'.pro.user')
        
        print 'Convert Done!'
        self.btnMake.setEnabled(True)
    
    def parse_mdkproj(self, mdkpath):
        root = et.parse(mdkpath).getroot()
        
        self.mdkproj['TargetName'] = root.find('Targets/Target/TargetName').text
        
        defines = root.find('Targets/Target/TargetOption/TargetArmAds/Cads/VariousControls/Define').text
        self.mdkproj['Defines'] = defines.replace(',', ' ').split() if defines else []
        
        incdirs = root.find('Targets/Target/TargetOption/TargetArmAds/Cads/VariousControls/IncludePath').text
        self.mdkproj['IncludePaths'] = incdirs.split(';') if incdirs else []

        self.mdkproj['Groups'] = {}
        for group in root.find('Targets/Target/Groups').iterfind('Group'):
            groupName = group.find('GroupName').text
            self.mdkproj['Groups'][groupName] = {}
            for file in group.find('Files').iterfind('File'):
                self.mdkproj['Groups'][groupName][file.find('FileName').text] = file.find('FilePath').text    
    
    def modify_pro(self, qtpro):
        text = open(qtpro, 'r').read()
        file = open(qtpro, 'w')
        
        DEFINES = 'DEFINES += \\\n'
        DEFINES += '\t' + '__CC_ARM' + ' \\\n'
        for defi in self.mdkproj['Defines']:
            DEFINES += '\t' + defi + ' \\\n'
        text += '\n' + DEFINES + '\n'
        
        if self.cmbMDKVer.currentText() == 'Keil MDK 4':
            key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 'UVPROJFILE\\Shell\\open\\command')
        else:
            key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 'UVPROJXFILE\\Shell\\open\\command')
        mdk_Uv4 = _winreg.QueryValue(key, '')
        mdk_inc = mdk_Uv4[1:mdk_Uv4.upper().rindex(r'UV4\UV4.EXE')]  + r'ARM\ARMCC\include'
        
        INCLUDEPATH = 'INCLUDEPATH += \\\n'
        INCLUDEPATH += '\t' + mdk_inc + ' \\\n'
        for path in self.mdkproj['IncludePaths']:
            INCLUDEPATH += '\t' + path.replace('\\', '/') + ' \\\n'
        text += '\n' + INCLUDEPATH + '\n'
        
        SOURCES = 'SOURCES += \\\n'
        DISTFILES = 'DISTFILES += \\\n'
        for group in self.mdkproj['Groups']:
            for path in self.mdkproj['Groups'][group]:
                if path.endswith('.c'):
                    SOURCES += '\t' + self.mdkproj['Groups'][group][path].replace('\\', '/') + ' \\\n'
                elif path.endswith('.s'):
                    DISTFILES += '\t' + self.mdkproj['Groups'][group][path].replace('\\', '/') + ' \\\n'
        text += '\n' + SOURCES + '\n\n' + DISTFILES + '\n'
        
        file.write(text)
        file.close()

    def modify_all(self, cfile, define, include):
        with open(define, 'w') as f:
            f.write('#define __CC_ARM\n')
            for defi in self.mdkproj['Defines']:
                f.write('#define %s\n' %defi.replace('=', ' '))

        if self.cmbMDKVer.currentText() == 'Keil MDK 4':
            key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 'UVPROJFILE\\Shell\\open\\command')
        else:
            key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 'UVPROJXFILE\\Shell\\open\\command')
        mdk_Uv4 = _winreg.QueryValue(key, '')
        mdk_inc = mdk_Uv4[1:mdk_Uv4.upper().rindex(r'UV4\UV4.EXE')]  + r'ARM\ARMCC\include'
        
        with open(include, 'w') as f:
            f.write(mdk_inc + '\n')
            for path in self.mdkproj['IncludePaths']:
                f.write(path.replace('\\', '/') + '\n')

        with open(cfile, 'w') as f:
            for group in self.mdkproj['Groups']:
                for path in self.mdkproj['Groups'][group]:
                    f.write(self.mdkproj['Groups'][group][path].replace('\\', '/').encode('gbk') + '\n')
    
    @QtCore.pyqtSlot()
    def on_btnExit_clicked(self):
        self.close()
    
    def closeEvent(self, evt):
        self.conf.set('globals', 'QT Version', self.cmbQTVer.currentText())
        self.conf.set('globals', 'MDK Version', self.cmbMDKVer.currentText())
        paths = []
        for i in range(min(10, self.cmbMDKPrj.count())):
            paths.append(self.cmbMDKPrj.itemText(i))
        self.conf.set('globals', 'MDK Projects', repr(paths))
        self.conf.write(open('setting.ini', 'w'))

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    win = MDK2QT()
    win.show()
    app.exec_()

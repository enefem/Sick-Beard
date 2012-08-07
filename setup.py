# coding=UTF-8
"""
Usage:
    python buildPackage.py
"""

from distutils.core import setup

import sys
import os
import re
import platform
import getopt
import shutil
import glob
from datetime import date
import subprocess
from subprocess import call, Popen
import urllib, ConfigParser
from distutils.core import setup
import zipfile, fnmatch
from lib.pygithub import github
# this is for the sublimnial support its the same as in SickBeard.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))

######################
# helper functions
# ascii art done here http://www.network-science.de/ascii/
def fancyLogoMac():
    return r"""
  _____ _      _    ____                     _    ____   _______   __
 / ____(_)    | |  |  _ \                   | |  / __ \ / ____\ \ / /
| (___  _  ___| | _| |_) | ___  __ _ _ __ __| | | |  | | (___  \ V / 
 \___ \| |/ __| |/ /  _ < / _ \/ _` | '__/ _` | | |  | |\___ \  > <  
 ____) | | (__|   <| |_) |  __/ (_| | | | (_| | | |__| |____) |/ . \ 
|_____/|_|\___|_|\_\____/ \___|\__,_|_|  \__,_|  \____/|_____//_/ \_\
"""
def fancyLogoWin():
    return r"""
  _____ _      _    ____                     _  __          ___       
 / ____(_)    | |  |  _ \                   | | \ \        / (_)      
| (___  _  ___| | _| |_) | ___  __ _ _ __ __| |  \ \  /\  / / _ _ __  
 \___ \| |/ __| |/ /  _ < / _ \/ _` | '__/ _` |   \ \/  \/ / | | '_ \ 
 ____) | | (__|   <| |_) |  __/ (_| | | | (_| |    \  /\  /  | | | | |
|_____/|_|\___|_|\_\____/ \___|\__,_|_|  \__,_|     \/  \/   |_|_| |_|
"""

def writeSickbeardVersionFile(version):
    sbVersionVarName = "SICKBEARD_VERSION"
    content = '%s = "%s"\n' % (sbVersionVarName, version)
    # write
    writeSickbeardVersionFileRaw(content)
    # now lets try to import the written file
    from sickbeard.version import SICKBEARD_VERSION
    if SICKBEARD_VERSION == version:
        return True
    else:
        return False

def writeSickbeardVersionFileRaw(content):
    # Create a file object:
    # in "write" mode
    versionFile = open(os.path.join("sickbeard", "version.py"), "w")
    versionFile.writelines(content)
    versionFile.close()

def readSickbeardVersionFile():
    versionFile = open(os.path.join("sickbeard", "version.py"), "r+")
    content = versionFile.read()
    return content

def getNiceOSString(buildParams):
    if (sys.platform == 'darwin' and buildParams['target'] == 'auto') or buildParams['target'] in ('osx', 'OSX', 'MAC'):
        return "OSX"
    elif (sys.platform == 'win32' and buildParams['target'] == 'auto')  or buildParams['target'] in ('win', 'WIN', 'Win32'):
        return "Win"
    else:
        return "unknown"

def getLatestCommitID(buildParams):
    gh = github.GitHub()
    newestCommit = ""
    for curCommit in gh.commits.forBranch('SickBeard-Team', 'SickBeard'):
        if newestCommit == "":
            longID = curCommit.id
            shortID = longID[:6]
            return (longID, shortID)

def getBranch(buildParams):
    branchRaw = subprocess.Popen(["git", "branch"], stdout=subprocess.PIPE).communicate()[0]

    regex = "(\* (\w+))"
    match = re.search(regex, branchRaw)
    if match:
        return match.group(2)
    else:
        return "unknown"

def writeChangelog(buildParams):
    # start building the CHANGELOG.txt
    print 'Creating / writing changelog'
    gh = github.GitHub()
    lastCommit = ""
    changeString = ""

    # cycle through all the git commits and save their commit messages
    for curCommit in gh.commits.forBranch('SickBeard-Team', 'SickBeard'):
        if curCommit.id == lastCommit:
            break
        curID = curCommit.id
        changeString += "#### %s ####\n%s\n" % (curID[:6], curCommit.message)

    # if we didn't find any changes don't make a changelog file
    if buildParams['gitNewestCommit'] != "":
        newChangelog = open(os.path.join('dist', "CHANGELOG.txt"), "w")
        newChangelog.write("Changelog for build " + str(buildParams['build']) + " (" + buildParams['gitNewestCommit'] + ")\n\n")
        newChangelog.write(changeString)
        newChangelog.close()
        print "changelog writen"
    else:
        print "No changes found, keeping old changelog"

def recursive_find_data_files(root_dir, allowed_extensions=('*')):
    to_return = {}
    for (dirpath, dirnames, filenames) in os.walk(root_dir):
        if not filenames:
            continue
        for cur_filename in filenames:
            matches_pattern = False
            for cur_pattern in allowed_extensions:
                if fnmatch.fnmatch(cur_filename, '*.' + cur_pattern):
                    matches_pattern = True
            if not matches_pattern:
                continue
            cur_filepath = os.path.join(dirpath, cur_filename)
            to_return.setdefault(dirpath, []).append(cur_filepath)

    return sorted(to_return.items())


def find_all_libraries(root_dirs):
    libs = []
    for cur_root_dir in root_dirs:
        for (dirpath, dirnames, filenames) in os.walk(cur_root_dir):
            if '__init__.py' not in filenames:
                continue
            libs.append(dirpath.replace(os.sep, '.'))

    return libs


def allFiles(dir):
    files = []
    for file in os.listdir(dir):
        fullFile = os.path.join(dir, file)
        if os.path.isdir(fullFile):
            files += allFiles(fullFile)
        else:
            files.append(fullFile)

    return files

#####################
#  build functions  #
#####################
def buildWIN(buildParams):
    #constants
    Win32ConsoleName = 'SickBeard-console.exe'
    Win32WindowName = 'SickBeard.exe'

    try:
        import py2exe
    except ImportError:
        print
        print 'ERROR you need py2exe to build a win binary http://www.py2exe.org/'
        return False

    # save the original arguments and replace them with the py2exe args
    oldArgs = []
    if len(sys.argv) > 1:
        oldArgs = sys.argv[1:]
        del sys.argv[1:]

    sys.argv.append('py2exe')

    # set up the compilation options
    data_files = recursive_find_data_files('data', ['gif', 'png', 'jpg', 'ico', 'js', 'css', 'tmpl'])

    options = dict(
        name=buildParams['name'],
        version=buildParams['build'],
        author='%s-Team' % buildParams['name'],
        author_email='sickbeard.team@gmail.com',
        description=buildParams['packageName'],
        scripts=[buildParams['mainPy']],
        packages=find_all_libraries(['sickbeard', 'lib']),
    )

    # set up py2exe to generate the console app
    program = [ {'script': buildParams['mainPy'] } ]
    options['options'] = {'py2exe':
                            {
                             'bundle_files': 3,
                             'packages': ['Cheetah'],
                             'excludes': ['Tkconstants', 'Tkinter', 'tcl'],
                             'optimize': 2,
                             'compressed': 0
                            }
                         }
    options['zipfile'] = 'lib/sickbeard.zip'
    options['console'] = program
    options['data_files'] = data_files

    if buildParams['test']:
        print
        print "########################################"
        print "NOT Building exe this was a TEST."
        print "########################################"
        return True

    # compile sickbeard-console.exe
    setup(**options)

    # rename the exe to sickbeard-console.exe
    try:
        if os.path.exists("dist/%s" % Win32ConsoleName):
            os.remove("dist/%s" % Win32ConsoleName)
        os.rename("dist/%s" % Win32WindowName, "dist/%s" % Win32ConsoleName)
    except:
        print
        print "########################################"
        print "Cannot create dist/%s" % Win32ConsoleName
        print "########################################"
        return False

    # we don't need this stuff when we make the 2nd exe
    del options['console']
    del options['data_files']
    options['windows'] = program

    # compile sickbeard.exe
    setup(**options)

    # compile sabToSickbeard.exe using the existing setup.py script

    auto_process_dir = 'autoProcessTV'
    p = subprocess.Popen([ sys.executable, 'setup.py' ], cwd=auto_process_dir)
    o, e = p.communicate()
    # copy autoProcessTV files to the dist dir
    auto_process_files = ['autoProcessTV/sabToSickBeard.py',
                          'autoProcessTV/hellaToSickBeard.py',
                          'autoProcessTV/autoProcessTV.py',
                          'autoProcessTV/autoProcessTV.cfg.sample',
                          'autoProcessTV/sabToSickBeard.exe']

    os.makedirs('dist/autoProcessTV')

    print
    print "########################################"
    print "Copy Files"
    print "########################################"
    for curFile in auto_process_files:
        newFile = os.path.join('dist', curFile)
        print "Copying file from", curFile, "to", newFile
        shutil.copy(curFile, newFile)

    # compile updater.exe
    setup(
          options={'py2exe': {'bundle_files': 1}},
          zipfile=None,
          console=['updater.py'],
    )

    print
    print "########################################"
    print 'Zipping files...'
    print "########################################"
    zipFilename = os.path.join('dist', buildParams['packageName'])

    # get a list of files to add to the zip
    zipFileList = allFiles('dist')
    # add all files to the zip
    z = zipfile.ZipFile(zipFilename + '.zip', 'w', zipfile.ZIP_DEFLATED)
    for file in zipFileList:
        z.write(file, file.replace('dist', buildParams['packageName']))
    z.close()

    print
    print "########################################"
    print "EXE build successful."
    print "ZIP is located at %s" % os.path.abspath(zipFilename)
    print "########################################"
    return True

def buildOSX(buildParams):
    # OSX constants
    bundleIdentifier = "com.sickbeard.sickbeard" # unique program identifier
    osxOriginalSpraseImageZip = "osx/template.sickbeard.sparseimage.zip" # 
    osxSpraseImage = "build/template.sickbeard.sparseimage"
    osxAppIcon = "osx/sickbeard.icns" # the app icon location
    osVersion = platform.mac_ver()[0]
    osVersionMayor, osVersionMinor, osVersionMicro = osVersion.split(".")
    osxDmg = "dist/%s.dmg" % buildParams['packageName'] # dmg file name/path

    try:
        import PyObjCTools
    except ImportError:
        print
        print "########################################"
        print 'WARNING PyObjCTools is not available'
        print 'this is included in the default python that comes with the system'
        print 'you can try: sudo easy_install pyobjc==2.2'
        print 'however the app can be build but the mac menu will be missing !!'
        print "########################################"

    try:
        import py2app
    except ImportError:
        print
        print 'ERROR you need py2app to build a mac app http://pypi.python.org/pypi/py2app/'
        return False

    #SickBeard-win32-alpha-build489.zip
    # Check which Python flavour
    apple_py = 'ActiveState' not in sys.copyright

    APP = [buildParams['mainPy']]
    DATA_FILES = ['data',
                  'sickbeard',
                  'lib',
                  ('', glob.glob("osx/resources/*"))]
    _NSHumanReadableCopyright = "(c) %s The %s-Team\nBuild on: %s %s\nBased on: %s\nPython used & incl: %s" % (buildParams['thisYearString'],
                                                                                                                    buildParams['name'],
                                                                                                                    buildParams['osName'],
                                                                                                                    osVersion,
                                                                                                                    buildParams['gitNewestCommit'],
                                                                                                                    str(sys.version))

    OPTIONS = {'argv_emulation': False,
               'iconfile': osxAppIcon,
               'packages':["email"],
               'plist': {'NSUIElement': 1,
                        'CFBundleShortVersionString': buildParams['build'],
                        'NSHumanReadableCopyright': _NSHumanReadableCopyright,
                        'CFBundleIdentifier': bundleIdentifier,
                        'CFBundleVersion' :  buildParams['build']
                        }
               }
    if len(sys.argv) > 1:
        sys.argv = [sys.argv[1]]
    for x in buildParams['py2AppArgs']:
        sys.argv.append(x)

    if buildParams['test']:
        print
        print "########################################"
        print "NOT Building App this was a TEST. Here are the names"
        print "########################################"
        print "volumeName: " + buildParams['packageName']
        print "osxDmg: " + osxDmg
        print "OPTIONS: " + str(OPTIONS)
        return True

    print
    print "########################################"
    print "Building App"
    print "########################################"
    setup(
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app'],
        )
    if buildParams['onlyApp']:
        print
        print "########################################"
        print "STOPING here you only wanted the App"
        print "########################################"
        return True

    print
    print "########################################"
    print "Build finished. Creating DMG"
    print "########################################"
    # unzip template sparse image
    call(["unzip", osxOriginalSpraseImageZip, "-d", "build"])

    # mount sparseimage and modify volumeName label
    os.system("hdiutil mount %s | grep /Volumes/SickBeard >build/mount.log" % (osxSpraseImage))

    # Select OSX version specific background image
    # Take care to preserve the special attributes of the background image file
    if buildParams['osxDmgImage']:
        if os.path.isfile(buildParams['osxDmgImage']):
            print "Writing new background image. %s ..." % os.path.abspath(buildParams['osxDmgImage']),
            # we need to read and write the data because otherwise we would lose the special hidden flag on the file
            f = open(buildParams['osxDmgImage'], 'rb')
            png = f.read()
            f.close()
            f = open('/Volumes/SickBeard/sb_osx.png', 'wb')
            f.write(png)
            f.close()
            print "ok"
        else:
            print "The provided image path is not a file"
    else:
        print "# Using default background image"

    # Rename the volumeName
    fp = open('build/mount.log', 'r')
    data = fp.read()
    fp.close()
    m = re.search(r'/dev/(\w+)\s+', data)
    print "Renaming the volume ...",
    if not call(["disktool", "-n", m.group(1), buildParams['packageName']], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

    #copy builded app to mounted sparseimage
    print "Copying SickBeard.app ...",
    if not call(["cp", "-r", "dist/SickBeard.app", "/Volumes/%s/" % buildParams['packageName']], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

    #copy scripts to mounted sparseimage
    print "Copying Scripts ...",
    if not call(["cp", "-r", "autoProcessTV/autoProcessTV.cfg.sample", "/Volumes/%s/Scripts/autoProcessTV.cfg" % buildParams['packageName']], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok",
    else:
        print "ERROR",
    if not call(["cp", "-r", "autoProcessTV/autoProcessTV.py", "/Volumes/%s/Scripts/" % buildParams['packageName']], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok",
    else:
        print "ERROR",
    if not call(["cp", "-r", "autoProcessTV/sabToSickBeard.py", "/Volumes/%s/Scripts/" % buildParams['packageName']], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

    print "# Sleeping 5 sec"
    os.system("sleep 5")
    #Unmount sparseimage
    print "Unmount sparseimage ...",
    if not call(["hdiutil", "eject", "/Volumes/%s/" % buildParams['packageName']], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

    #Convert sparseimage to read only compressed dmg
    print "Convert sparseimage to read only compressed dmg ...",
    if not call(["hdiutil", "convert", osxSpraseImage, "-format", "UDBZ", "-o", osxDmg], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

    #Make image internet-enabled
    print "Make image internet-enabled ...",
    if not call(["hdiutil", "internet-enable", osxDmg], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

    print
    print "########################################"
    print "App build successful."
    print "DMG is located at %s" % os.path.abspath(osxDmg)
    print "########################################"
    return True

def main():
    print
    print "########################################"
    print "Starting build ..."
    print "########################################"


    buildParams = {}
    ######################
    # check arguments
    # defaults
    buildParams['test'] = False
    buildParams['target'] = 'auto'
    buildParams['nightly'] = False
    buildParams['year'] = ""
    buildParams['month'] = ""
    buildParams['day'] = ""
    buildParams['branch'] = ""
    # win
    buildParams['py2ExeArgs'] = [] # not used yet
    # osx
    buildParams['onlyApp'] = False
    buildParams['py2AppArgs'] = ['py2app']
    buildParams['osxDmgImage'] = ""


    try:
        opts, args = getopt.getopt(sys.argv[1:], "", [ 'test', 'onlyApp', 'nightly', 'dmgbg=', 'py2appArgs=', 'target=', 'year=', 'month=', 'day=', 'branch=']) #@UnusedVariable
    except getopt.GetoptError:
        print "Available options: --test, --dmgbg, --onlyApp, --nightly, --py2appArgs, --target, --year, --month, --day, --branch"
        exit(1)

    for o, a in opts:
        if o in ('--test'):
            buildParams['test'] = True

        if o in ('--nightly'):
            buildParams['nightly'] = True

        if o in ('--dmgbg'):
            buildParams['osxDmgImage'] = a

        if o in ('--onlyApp'):
            buildParams['onlyApp'] = True

        if o in ('--py2appArgs'):
            buildParams['py2AppArgs'] = py2AppArgs + a.split()

        if o in ('--dmgbg'):
            buildParams['osxDmgImage'] = a

        if o in ('--target'):
            buildParams['target'] = a

        if o in ('--year'):
            buildParams['year'] = a

        if o in ('--month'):
            buildParams['month'] = a

        if o in ('--day'):
            buildParams['day'] = a

        if o in ('--branch'):
            buildParams['branch'] = a

    ######################
    # constants
    buildParams['mainPy'] = "SickBeard.py" # this should never change
    buildParams['name'] = "SickBeard" # this should never change
    buildParams['majorVersion'] = "alpha" # one day we will change that to BETA :P

    buildParams['osName'] = getNiceOSString(buildParams); # look in getNiceOSString() for default os nice names

    """
    # maybe some day the git tag is used this might be handy although it might be easier ti use the github lib
    # dynamic build number and date stuff
    tagsRaw = subprocess.Popen(["git", "tag"], stdout=subprocess.PIPE).communicate()[0]
    lastTagRaw = tagsRaw.split("\n")[-2] # current tag e.g. build-###
    tag = lastTagRaw.split("-")[1] # current tag pretty... change according to tag scheme
    """
    # date stuff
    buildParams['thisYearString'] = date.today().strftime("%Y") # for the copyright notice

    if not buildParams['year']:
        buildParams['year'] = date.today().strftime("%y")
    if not buildParams['month']:
        buildParams['month'] = date.today().strftime("%m")
    if buildParams['day'] == 'auto':
        buildParams['day'] = date.today().strftime("%d")

    if buildParams['day']:
        buildParams['dateVersion'] = "%s.%s.%s" % (buildParams['year'], buildParams['month'], buildParams['day'])
    else:
        buildParams['dateVersion'] = "%s.%s" % (buildParams['year'], buildParams['month'])

    # buildParams['gitLastCommit'] = subprocess.Popen(["git", "describe", "--tag"], stdout=subprocess.PIPE).communicate()[0].strip().split("-")[2] # bet there is a simpler way

    buildParams['gitNewestCommit'], buildParams['gitNewestCommitShort'] = getLatestCommitID(buildParams)
    if not buildParams['branch']:
        buildParams['branch'] = getBranch(buildParams)

    # this is the 'branch yy.mm(.dd)' string
    buildParams['build'] = "%s %s" % (buildParams['branch'], buildParams['dateVersion'])
    # or for nightlys yy.mm.commit
    if buildParams['nightly']:
        buildParams['build'] = "%s.%s" % (buildParams['dateVersion'], buildParams['gitNewestCommitShort'])

    # the new SICKBEARD_VERSION string visible to the user and used in the binary package file name
    buildParams['newSBVersion'] = "%s %s" % (buildParams['osName'], buildParams['build'])

    print "backup SickbeardVersionFile ...",
    oldSickbeardVersionFile = readSickbeardVersionFile()
    if not oldSickbeardVersionFile:
        print "ERROR"
        print "seams like reading the verision.py file failed. permissions ?"
        exit(1)
    else:
        print "ok"

    print "setting SICKBEARD_VERSION to %s ..." % (buildParams['newSBVersion']),
    if not writeSickbeardVersionFile(buildParams['newSBVersion']):
        print "ERROR"
        print "seams like writing the verision.py file failed. permissions ?"
        exit(1)
    else:
        print "ok"

    buildParams['packageName'] = "%s-%s-%s" % (buildParams['name'] , buildParams['osName'] , buildParams['build']) # volume name
    buildParams['packageName'] = buildParams['packageName'].replace(" ","-")
    #####################
    # clean the build dirs
    if not buildParams['test']:
        print "Removing old build dirs ...",
        # remove old build stuff
        if os.path.exists('build'):
            shutil.rmtree('build')
        if os.path.exists('dist'):
            shutil.rmtree('dist')
        # a windows build creats these folder too ... clear them
        scriptBuild = os.path.join('autoProcessTV', 'build')
        scriptDist = os.path.join('autoProcessTV', 'dist')
        if os.path.exists(scriptBuild):
            shutil.rmtree(scriptBuild)
        if os.path.exists(scriptDist):
            shutil.rmtree(scriptDist)
        # create build dirs acctualy only the dist has to be made manual because the changelog will be writen there
        os.makedirs('build') # create tmp build dir
        os.makedirs('dist') # create tmp build dir
        # TODO: do some real testing and dont just say ok
        print "ok"
    #####################
    # write changelog
    writeChangelog(buildParams)


    curFancyLogo = ""


    # os switch
    if buildParams['osName'] == 'OSX':
        result = buildOSX(buildParams)
        curFancyLogo = fancyLogoMac()
    elif buildParams['osName'] == 'Win':
        result = buildWIN(buildParams)
        curFancyLogo = fancyLogoWin()
    else:
        print "unknown os/target valid: mac, win"
        result = False

    if result:
        # lets do some clean up
        writeSickbeardVersionFileRaw(oldSickbeardVersionFile) # rewrite the version.py
        # remove the temp build dirs
        if os.path.exists('build'):
            shutil.rmtree('build')
        if os.path.exists(scriptBuild):
            shutil.rmtree(scriptBuild)
        print curFancyLogo
        print
        print "########################################"
        print "Build SUCCESSFUL !!"
        print "########################################"
        exit()
    else:
        print
        print "########################################"
        print "ERROR during build ... i have failed you"
        print "########################################"
        exit(1)

if __name__ == '__main__':
    main()


#!/usr/bin/env python
import os
import sys
import subprocess
import shutil
import atexit
import datetime
import time
import tempfile
import re
import curses

# Environment variables
os.environ["LOGOS_SCRIPT_TITLE"] = "Logos Linux Installer"
os.environ["LOGOS_SCRIPT_AUTHOR"] = "Ferion11, John Goodman, T. H. Wright"
os.environ["LOGOS_SCRIPT_VERSION"] = "3.7.5"
os.environ["WINE64_APPIMAGE_FULL_VERSION"] = "v7.18-staging"
os.environ["WINE64_APPIMAGE_FULL_URL"] = "https://github.com/ferion11/LogosLinuxInstaller/releases/download/wine-devel-8.19/wine-devel_8.19-x86_64.AppImage"
os.environ["WINE64_APPIMAGE_FULL_FILENAME"] = os.path.basename(os.environ["WINE64_APPIMAGE_FULL_URL"])
os.environ["WINE64_APPIMAGE_VERSION"] = "v7.18-staging"
os.environ["WINE64_APPIMAGE_URL"] = "https://github.com/ferion11/LogosLinuxInstaller/releases/download/v10.0-1/wine-staging_7.18-x86_64.AppImage"
os.environ["WINE64_BOTTLE_TARGZ_URL"] = "https://github.com/ferion11/wine64_bottle_dotnet/releases/download/v5.11b/wine64_bottle.tar.gz"
os.environ["WINE64_BOTTLE_TARGZ_NAME"] = "wine64_bottle.tar.gz"
os.environ["WINE64_APPIMAGE_FILENAME"] = os.path.basename(os.environ["WINE64_APPIMAGE_URL"]).split(".AppImage")[0]
os.environ["APPIMAGE_LINK_SELECTION_NAME"] = "selected_wine.AppImage"
os.environ["WINETRICKS_URL"] = "https://raw.githubusercontent.com/Winetricks/winetricks/5904ee355e37dff4a3ab37e1573c56cffe6ce223/src/winetricks"
os.environ["LAUNCHER_TEMPLATE_URL"] = "https://raw.githubusercontent.com/ferion11/LogosLinuxInstaller/master/Launcher-Template.sh"
os.environ["CONTROL_PANEL_TEMPLATE_URL"] = "https://raw.githubusercontent.com/ferion11/LogosLinuxInstaller/master/controlPanel-Template.sh"
os.environ["WINETRICKS_DOWNLOADER"] = "wget"
os.environ["WINETRICKS_UNATTENDED"] = ""
os.environ["WORKDIR"] = tempfile.mkdtemp(prefix="/tmp/LBS.")
os.environ["PRESENT_WORKING_DIRECTORY"] = os.getcwd()
os.environ.setdefault("LOGOS_FORCE_ROOT", "")
os.environ.setdefault("WINEBOOT_GUI", "")
os.environ["EXTRA_INFO"] = "The following packages are usually necessary: winbind cabextract libjpeg8."
os.environ.setdefault("DEFAULT_CONFIG_PATH", os.path.expanduser("~/.config/Logos_on_Linux/Logos_on_Linux.conf"))
os.environ.setdefault("LOGOS_LOG", os.path.expanduser("~/.local/state/Logos_on_Linux/install.log"))
os.makedirs(os.path.dirname(os.environ["LOGOS_LOG"]), exist_ok=True)
open(os.environ["LOGOS_LOG"], "a").close()
os.environ.setdefault("WINEDEBUG", "fixme-all,err-all")
os.environ.setdefault("DEBUG", "FALSE")
os.environ.setdefault("VERBOSE", "FALSE")

def usage():
    with open(PIDF, 'r') as file:
        print(file.read())

def die_if_running():
    PIDF = '/tmp/LogosLinuxInstaller.pid'
    
    if os.path.isfile(PIDF):
        with open(PIDF, 'r') as f:
            pid = f.read().strip()
            if logos_continue_question("The script is already running on PID {}. Should it be killed to allow this instance to run?".format(pid), "The script is already running. Exiting.", "1"):
                os.kill(int(pid), signal.SIGKILL)
    
    def remove_pid_file():
        if os.path.exists(PIDF):
            os.remove(PIDF)
    
    atexit.register(remove_pid_file)
    with open(PIDF, 'w') as f:
        f.write(str(os.getpid()))

def die_if_root():
    if os.getuid() == 0 and not LOGOS_FORCE_ROOT:
        logos_error("Running Wine/winetricks as root is highly discouraged. Use -f|--force-root if you must run as root. See https://wiki.winehq.org/FAQ#Should_I_run_Wine_as_root.3F")

def verbose():
    return os.environ["VERBOSE"]

def debug():
    return DEBUG

def setDebug():
    global DEBUG, VERBOSE, WINEDEBUG
    DEBUG = True
    VERBOSE = True
    WINEDEBUG = ""
    subprocess.run(['set', '-x'])
    with open(LOGOS_LOG, 'a') as file:
        file.write("Debug mode enabled.\n")

def die(message):
    print(message, file=sys.stderr)
    sys.exit(1)

def t(command):
    try:
        subprocess.run(['which', command], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def getDialog():
    if not os.environ.get('DISPLAY'):
        logos_error("The installer does not work unless you are running a display")
        sys.exit(1)

    DIALOG = ""
    DIALOG_ESCAPE = ""
    GUI = ""

    if os.isatty(0):
        if t("whiptail"):
            DIALOG = "whiptail"
        elif t("dialog"):
            DIALOG = "dialog"
            DIALOG_ESCAPE = "--"
            os.environ['DIALOG_ESCAPE'] = DIALOG_ESCAPE
        else:
            if os.environ.get('XDG_CURRENT_DESKTOP') != "KDE":
                if t("zenity"):
                    DIALOG = "zenity"
                    GUI = True
                # elif t("kdialog"):
                #     DIALOG = "kdialog"
                #     GUI = True
            elif os.environ.get('XDG_CURRENT_DESKTOP') == "KDE":
                # if t("kdialog"):
                #     DIALOG = "kdialog"
                #     GUI = True
                if t("zenity"):
                    DIALOG = "zenity"
                    GUI = True
            else:
                print("No dialog program found. Please install either dialog, whiptail, zenity, or kdialog")
                sys.exit(1)
    else:
        if os.environ.get('XDG_CURRENT_DESKTOP') != "KDE":
            if t("zenity"):
                DIALOG = "zenity"
                GUI = True
        elif os.environ.get('XDG_CURRENT_DESKTOP') == "KDE":
            # if t("kdialog"):
            #     DIALOG = "kdialog"
            #     GUI = True
            if t("zenity"):
                DIALOG = "zenity"
                GUI = True
        else:
            no_diag_msg("No dialog program found. Please install either zenity or kdialog.")
            sys.exit(1)

    os.environ['DIALOG'] = DIALOG
    os.environ['GUI'] = GUI

def have_dep(cmd):
    try:
        subprocess.run(["command -v", cmd], shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def clean_all():
    logos_info("Cleaning all temp files…")
    os.system("rm -fr /tmp/LBS.*")
    os.system("rm -fr {WORKDIR}")
    logos_info("done")

def light_wineserver_wait():
    os.system(f"{WINESERVER_EXE} -w | logos_progress 'Waiting for {WINE_EXE} to end properly…' 'Waiting for {WINE_EXE} to end properly…'")

def heavy_wineserver_wait():
    wait_process_using_dir(WINEPREFIX) | logos_progress("Waiting for {WINE_EXE} to end properly…", "Waiting for {WINE_EXE} to end properly…")
    os.system(f"{WINESERVER_EXE} -w | logos_progress 'Waiting for {WINE_EXE} proper end' 'Waiting for {WINE_EXE} to end properly…'")

def mkdir_critical(directory):
    try:
        os.mkdir(directory)
    except OSError:
        logos_error(f"Can't create the {directory} directory")

def no_diag_msg(message):
    with open(LOGOS_LOG, "a") as file:
        file.write(message + "\n")
    subprocess.Popen(["xterm", "-hold", "-e", "printf", "%s" % message])
    die()

def cli_msg(message):
    print(message)

def gtk_info(*args):
    subprocess.Popen(["zenity", "--info", "--width=300", "--height=200", "--text=" + " ".join(args), "--title=Information"])
    
def gtk_progress(title, text):
    subprocess.Popen(["zenity", "--progress", "--title=" + title, "--text=" + text, "--pulsate", "--auto-close", "--no-cancel"])
    
def gtk_warn(*args):
    subprocess.Popen(["zenity", "--warning", "--width=300", "--height=200", "--text=" + " ".join(args), "--title=Warning!"])
    
def gtk_error(*args):
    subprocess.Popen(["zenity", "--error", "--width=300", "--height=200", "--text=" + " ".join(args), "--title=Error!"])   

def logos_info(message):
    if DIALOG in ["whiptail", "dialog"]:
        cli_msg(message)
    elif DIALOG == "zenity":
        gtk_info(message)
        with open(LOGOS_LOG, "a") as file:
            file.write(f"{datetime.now()} {message}\n")
    elif DIALOG == "kdialog":
        pass

def logos_progress(title, text):
    if DIALOG in ["whiptail", "dialog"]:
        cli_msg(text)
    elif DIALOG == "zenity":
        gtk_progress(title, text)
    elif DIALOG == "kdialog":
        pass
    
def logos_warn(message):
    if DIALOG in ["whiptail", "dialog"]:
        cli_msg(message)
    elif DIALOG == "zenity":
        gtk_warn(message)
        with open(LOGOS_LOG, "a") as file:
            file.write(f"{datetime.now()} {message}\n")
    elif DIALOG == "kdialog":
        pass

def logos_error(message, secondary):
    WIKI_LINK = "https://github.com/ferion11/LogosLinuxInstaller/wiki"
    TELEGRAM_LINK = "https://t.me/linux_logos"
    MATRIX_LINK = "https://matrix.to/#/#logosbible:matrix.org"
    help_message = f"If you need help, please consult:\n{WIKI_LINK}\n{TELEGRAM_LINK}\n{MATRIX_LINK}"
    DIALOG = os.environ.get('DIALOG')
    if DIALOG in ["whiptail", "dialog"]:
        cli_msg(message + "\n" + help_message)
    elif DIALOG == "zenity":
        gtk_error(message + "\n" + help_message)
        with open(LOGOS_LOG, "a") as file:
            file.write(f"{datetime.now()} {message}\n")
    elif DIALOG == "kdialog":
        pass
    if not secondary:
        subprocess.run(["rm", "/tmp/LogosLinuxInstaller.pid"])
        pgid = subprocess.check_output(['ps', '-o', 'pgid=', '-p', str(os.getpid())]).decode().strip()
        subprocess.run(['kill', '-SIGKILL', '-'+pgid], check=True)
    exit(1)

def cli_question(QUESTION_TEXT):
    while True:
        yn = input(f"{QUESTION_TEXT} [Y/n]: ")
        
        if yn.lower() == 'y':
            return True
        elif yn.lower() == 'n':
            return False
        else:
            print("Type Y[es] or N[o].")
            
def cli_continue_question(QUESTION_TEXT, NO_TEXT, SECONDARY):
    if not cli_question(QUESTION_TEXT):
        logos_error(NO_TEXT, SECONDARY)
        
def cli_acknowledge_question(QUESTION_TEXT, NO_TEXT):
    if not cli_question(QUESTION_TEXT):
        logos_info(NO_TEXT)
        
def gtk_question(*args):
    try:
        subprocess.run(['zenity', '--question', '--width=300', '--height=200', '--text', *args, '--title=Question:'])
        return True
    except subprocess.CalledProcessError:
        return False
        
def gtk_continue_question(QUESTION_TEXT, NO_TEXT, SECONDARY):
    if not gtk_question(QUESTION_TEXT):
        logos_error('The installation was cancelled!', SECONDARY)
        
def gtk_acknowledge_question(QUESTION_TEXT, NO_TEXT):
    if not gtk_question(QUESTION_TEXT):
        logos_info(NO_TEXT)
        
def logos_continue_question(QUESTION_TEXT, NO_TEXT, SECONDARY):
    if os.environ.get('DIALOG') == 'whiptail' or os.environ.get('DIALOG') == 'dialog':
        cli_continue_question(QUESTION_TEXT, NO_TEXT, SECONDARY)
    elif os.environ.get('DIALOG') == 'zenity':
        gtk_continue_question(QUESTION_TEXT, NO_TEXT, SECONDARY)
    elif os.environ.get('DIALOG') == 'kdialog':
        pass
        
def logos_acknowledge_question(QUESTION_TEXT, NO_TEXT):
    if os.environ.get('DIALOG') == 'whiptail' or os.environ.get('DIALOG') == 'dialog':
        cli_acknowledge_question(QUESTION_TEXT, NO_TEXT)
    elif os.environ.get('DIALOG') == 'zenity':
        gtk_acknowledge_question(QUESTION_TEXT, NO_TEXT)
    elif os.environ.get('DIALOG') == 'kdialog':
        pass

def cli_download(uri, destination):
    filename = os.path.basename(uri)

    if destination != destination.rstrip('/'):
        target = os.path.join(destination, os.path.basename(uri))
        if not os.path.isdir(destination):
            os.makedirs(destination)
    elif os.path.isdir(destination):
        target = os.path.join(destination, os.path.basename(uri))
    else:
        target = destination
        dirname = os.path.dirname(destination)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

    subprocess.call(['wget', '-c', uri, '-O', target])

def gtk_download(uri, destination):
    filename = os.path.basename(uri)

    if destination != destination.rstrip('/'):
        target = os.path.join(destination, os.path.basename(uri))
        if not os.path.isdir(destination):
            os.makedirs(destination)
    elif os.path.isdir(destination):
        target = os.path.join(destination, os.path.basename(uri))
    else:
        target = destination
        dirname = os.path.dirname(destination)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

    pipe_progress = subprocess.Popen(['mktemp'], stdout=subprocess.PIPE).communicate()[0].decode().strip()
    os.mkfifo(pipe_progress)

    pipe_wget = subprocess.Popen(['mktemp'], stdout=subprocess.PIPE).communicate()[0].decode().strip()
    os.mkfifo(pipe_wget)

    subprocess.Popen(['zenity', '--progress', '--title', f'Downloading {filename}...', '--text', f'Downloading: {filename}\ninto: {destination}\n', '--percentage=0', '--auto-close', pipe_wget],
                     stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

    total_size = "Starting..."
    percent = 0
    current = "Starting..."
    speed = "Starting..."
    remain = "Starting..."

    with open(pipe_progress) as progress:
        for data in progress:
            if data.startswith('Length:'):
                result = data.split('(')[-1].split(')')[0].strip()
                if len(result) <= 10:
                    total_size = result

            if any(x.isdigit() for x in data):
                result = next((x for x in data if x.isdigit()), None)
                if len(result) <= 3:
                    percent = int(result)

                result = ''.join(x for x in data if x.isdigit() or x in ['B', 'K', 'M', 'G'])
                if len(result) <= 10:
                    current = result

                result = ''.join(x for x in data if x.isdigit() or x in ['B', 'K', 'M', 'G', '.'])
                if len(result) <= 10:
                    speed = result

                result = ''.join(x for x in data if x.isalnum())
                if len(result) <= 10:
                    remain = result

            if subprocess.call(['pgrep', '-P', str(os.getpid()), 'zenity']) == 0:
                wget_pid_current = subprocess.check_output(['pgrep', '-P', str(os.getpid()), 'wget']).decode().strip()
                if wget_pid_current:
                    subprocess.call(['kill', '-SIGKILL', wget_pid_current])

            if percent == 100:
                break

            # Update zenity's progress bar
            print(percent)
            print(f"#Downloading: {filename}\ninto: {destination}\n{current} of {total_size} ({percent}%)\nSpeed: {speed}/Sec Estimated time: {remain}")

        subprocess.call(['wait', str(os.getpid())])
        wget_return = subprocess.call(['wait', str(os.getpid())])

        subprocess.call(['fuser', '-TERM', '-k', '-w', pipe_progress])
        os.remove(pipe_progress)

        subprocess.call(['fuser', '-TERM', '-k', '-w', pipe_wget])
        os.remove(pipe_wget)

        if wget_return != 0 and wget_return != 127:
            raise Exception("ERROR: The installation was cancelled because of an error while attempting a download.\nAttmpted Downloading: {uri}\nTarget Destination: {destination}\nFile Name: {filename}\n- Error Code: WGET_RETURN: {wget_return}")

    print(f"{filename} download finished!")

def logos_download(uri, destination):
    if os.environ.get('DIALOG') == 'whiptail' or os.environ.get('DIALOG') == 'dialog':
        cli_download(uri, destination)
    elif os.environ.get('DIALOG') == 'zenity':
        gtk_download(uri, destination)
    elif os.environ.get('DIALOG') == 'kdialog':
        raise NotImplementedError("kdialog not implemented.")
    else:
        raise Exception("No dialog tool found.")

def logos_reuse_download(SOURCEURL, FILE, TARGETDIR):
    DOWNLOADS = os.path.expanduser("~/Downloads")
    DIRS = [
        INSTALLDIR,
        os.getcwd(),
        DOWNLOADS
    ]
    FOUND = 1
    for i in DIRS:
        if os.path.isfile(os.path.join(i, FILE)):
            logos_info(f"{FILE} exists in {i}. Using it…")
            shutil.copy(os.path.join(i, FILE), TARGETDIR)
            logos_progress("Copying…", f"Copying {FILE}\ninto {TARGETDIR}")
            FOUND = 0
            break
    if FOUND == 1:
        logos_info(f"{FILE} does not exist. Downloading…")
        logos_download(SOURCEURL, os.path.join(DOWNLOADS, FILE))
        shutil.copy(os.path.join(DOWNLOADS, FILE), TARGETDIR)
        logos_progress("Copying…", f"Copying: {FILE}\ninto: {TARGETDIR}")

def getAppImage():
    logos_reuse_download(WINE64_APPIMAGE_FULL_URL, WINE64_APPIMAGE_FULL_FILENAME, APPDIR_BINDIR)

def wait_process_using_dir(directory):
    VERIFICATION_DIR = directory
    VERIFICATION_TIME = 7
    VERIFICATION_NUM = 3

    verbose()
    print("* Starting wait_process_using_dir…")
    i = 0
    while True:
        i += 1
        verbose()
        print(f"wait_process_using_dir: loop with i={i}")

        print(f"wait_process_using_dir: sleep {VERIFICATION_TIME}")
        time.sleep(VERIFICATION_TIME)

        FIST_PID = subprocess.check_output(["lsof", "-t", VERIFICATION_DIR]).decode().split("\n")[0]
        verbose()
        print(f"wait_process_using_dir FIST_PID: {FIST_PID}")
        if FIST_PID:
            i = 0
            verbose()
            print(f"wait_process_using_dir: tail --pid={FIST_PID} -f /dev/null")
            subprocess.run(["tail", "--pid", FIST_PID, "-f", "/dev/null"])
            continue

        if i >= VERIFICATION_NUM:
            break
    verbose()
    print("* End of wait_process_using_dir.")

def make_skel(SET_APPIMAGE_FILENAME):
    INSTALLDIR = ""
    APPDIR = ""
    APPDIR_BINDIR = ""

    SET_APPIMAGE_FILENAME = SET_APPIMAGE_FILENAME

    verbose()
    print(f"* Making skel64 inside {INSTALLDIR}")
    subprocess.run(["mkdir", "-p", INSTALLDIR])
    subprocess.run(["mkdir", APPDIR]) or die(f"can't make dir: {APPDIR}")
    subprocess.run(["mkdir", APPDIR_BINDIR]) or die(f"can't make dir: {APPDIR_BINDIR}")

    # Making the links
    subprocess.run(["cd", APPDIR_BINDIR]) or die(f"ERROR: Can't open dir: {APPDIR_BINDIR}")
    subprocess.run(["ln", "-s", SET_APPIMAGE_FILENAME, f"{APPDIR_BINDIR}/{APPIMAGE_LINK_SELECTION_NAME}"])
    subprocess.run(["ln", "-s", f"{APPIMAGE_LINK_SELECTION_NAME}", "wine"])
    subprocess.run(["ln", "-s", f"{APPIMAGE_LINK_SELECTION_NAME}", "wine64"])
    subprocess.run(["ln", "-s", f"{APPIMAGE_LINK_SELECTION_NAME}", "wineserver"])
    subprocess.run(["cd", "-"]) or die("ERROR: Can't go back to preview dir!")

    subprocess.run(["mkdir", f"{APPDIR}/wine64_bottle"])

    verbose()
    print("skel64 done!")

def check_commands(*cmds):
    MISSING_CMD = []
    for cmd in cmds:
        if have_dep(cmd):
            if verbose:
                print(f"* command {cmd} is installed!")
        else:
            if verbose:
                print(f"* command {cmd} not installed!")
            MISSING_CMD.append(cmd)
    
    if len(MISSING_CMD) != 0:
        logos_error(f"Your system is missing {' '.join(MISSING_CMD)}. Please install your distro's {' '.join(MISSING_CMD)} package(s).\n {EXTRA_INFO}")

def have_lib(lib):
    try:
        subprocess.check_output(["ldconfig -N -v", lib])
        return True
    except FileNotFoundError:
        return False

def check_libs(*libs):
    for lib in libs:
        if have_lib(lib):
            verbose()
            print(f"* {lib} is installed!")
        else:
            logos_error(f"Your system does not have lib: {lib}. Please install {lib} package.\n {EXTRA_INFO}")

def checkDependencies():
    verbose()
    print("Checking system's for dependencies:")
    check_commands("mktemp", "patch", "lsof", "wget", "find", "sed", "grep", "ntlm_auth", "awk", "tr", "bc", "xmllint", "curl")

def checkDependenciesLogos10():
    verbose()
    print("All dependencies found. Continuing…")

def checkDependenciesLogos9():
    verbose()
    print("Checking dependencies for Logos 9.")
    check_commands("xwd", "cabextract");
    verbose()
    print("All dependencies found. Continuing…")

def chooseProduct():
    BACKTITLE = "Choose Product Menu"
    TITLE = "Choose Product"
    QUESTION_TEXT = "Choose which FaithLife product the script should install:"
    if not os.environ.get("FLPRODUCT"):
        DIALOG = os.environ.get("DIALOG")
        if DIALOG in ["whiptail", "dialog"]:
            # Set up the screen
            stdscr = curses.initscr()
            curses.curs_set(0)
            stdscr.nodelay(1)
            stdscr.timeout(100)
        
            # Define the options for the radio list
            options = ["Logos", "Verbum", "Exit"]
            current_option = 0
        
            while True:
                stdscr.clear()
                height, width = stdscr.getmaxyx()
        
                # Display the radio list options
                for i, option in enumerate(options):
                    x = width//2 - len(option)//2
                    y = height//2 - len(options)//2 + i
                    if i == current_option:
                        stdscr.attron(curses.A_REVERSE)
                        stdscr.addstr(y, x, option)
                        stdscr.attroff(curses.A_REVERSE)
                    else:
                        stdscr.addstr(y, x, option)
        
                # Get user input
                key = stdscr.getch()

                # Process user input
                if key == curses.KEY_UP:
                    current_option = max(0, current_option-1)
                elif key == curses.KEY_DOWN:
                    current_option = min(len(options)-1, current_option+1)
                elif key == ord('\n'):  # User presses Enter
                    productChoice = options[current_option]
                    break
            curses.endwin()
        elif DIALOG == "zenity":
            process = subprocess.Popen(["zenity", "--width=700", "--height=310", "--title=" + TITLE, "--text=" + QUESTION_TEXT, "--list", "--radiolist", "--column", "S", "--column", "Description", "TRUE", "Logos Bible Software.", "FALSE", "Verbum Bible Software.", "FALSE", "Exit."], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            productChoice, _ = process.communicate()
        elif DIALOG == "kdialog":
            sys.exit("kdialog not implemented.")
        else:
            sys.exit("No dialog tool found")
    else:
        productChoice = os.environ.get("FLPRODUCT")

    print("productChoice:" + str(productChoice))
    if str(productChoice).startswith("Logos"):
        verbose()
        print("Installing Logos Bible Software")
        os.environ["FLPRODUCT"] = "Logos"
        os.environ["FLPRODUCTi"] = "logos4" #This is the variable referencing the icon path name in the repo.
    elif str(productChoice).startswith("Verbum"):
        verbose()
        print("Installing Verbum Bible Software")
        os.environ["FLPRODUCT"] = "Verbum"
        os.environ["FLPRODUCTi"] = "verbum" #This is the variable referencing the icon path name in the repo.
        os.environ["VERBUM_PATH"] = "Verbum/"
    elif str(productChoice).startswith("Exit"):
        logos_error("Exiting installation.", "")
    else:
        logos_error("Unknown product. Installation canceled!", "")

    if not os.environ.get("LOGOS_ICON_URL"):
        os.environ["LOGOS_ICON_URL"] = "https://raw.githubusercontent.com/ferion11/LogosLinuxInstaller/master/img/" + os.environ.get("FLPRODUCTi") + "-128-icon.png"

def chooseVersion():
    TARGETVERSION = os.environ.get('TARGETVERSION')
    DIALOG = os.environ.get('DIALOG')
    BACKTITLE = "Choose Version Menu"
    TITLE = "Choose Product Version"
    QUESTION_TEXT = f"Which version of {os.environ.get('FLPRODUCT')} should the script install?"
    if TARGETVERSION is None or TARGETVERSION == "":
        if DIALOG == "whiptail" or DIALOG == "dialog":
            if DIALOG in ["whiptail", "dialog"]:
                # Set up the screen
                stdscr = curses.initscr()
                curses.curs_set(0)
                stdscr.nodelay(1)
                stdscr.timeout(100)
        
                # Define the options for the radio list
                options = ["10", "9", "Exit"]
                current_option = 0
        
                while True:
                    stdscr.clear()
                    height, width = stdscr.getmaxyx()
        
                    # Display the radio list options
                    for i, option in enumerate(options):
                        x = width//2 - len(option)//2
                        y = height//2 - len(options)//2 + i
                        if i == current_option:
                            stdscr.attron(curses.A_REVERSE)
                            stdscr.addstr(y, x, option)
                            stdscr.attroff(curses.A_REVERSE)
                        else:
                            stdscr.addstr(y, x, option)
        
                    # Get user input
                    key = stdscr.getch()
        
                    # Process user input
                    if key == curses.KEY_UP:
                        current_option = max(0, current_option-1)
                    elif key == curses.KEY_DOWN:
                        current_option = min(len(options)-1, current_option+1)
                    elif key == ord('\n'):  # User presses Enter
                        versionChoice = options[current_option]
                        break
                curses.endwin()
        elif DIALOG == "zenity":
            command = ["zenity", "--width=700", "--height=310", "--title", TITLE, "--text", QUESTION_TEXT, "--list", "--radiolist", "--column", "S", "--column", "Description", "TRUE", f"{FLPRODUCT} 10", "FALSE", f"{FLPRODUCT} 9", "FALSE", "Exit"]
            versionChoice = subprocess.check_output(command, stderr=subprocess.STDOUT).decode().strip()
        elif DIALOG == "kdialog":
            no_diag_msg("kdialog not implemented.")
        else:
            no_diag_msg("No dialog tool found.")
    else:
        versionChoice = TARGETVERSION
    
    if "10" in versionChoice:
        checkDependenciesLogos10()
        TARGETVERSION = "10"
    elif "9" in versionChoice:
        checkDependenciesLogos9()
        TARGETVERSION = "9"
    elif versionChoice == "Exit.":
        exit()
    else:
        logos_error("Unknown version. Installation canceled!")

    LOGOS_RELEASE_VERSION = subprocess.check_output(["curl", "-s", f"https://clientservices.logos.com/update/v1/feed/logos{TARGETVERSION}/stable.xml"]).decode().strip()
    LOGOS_RELEASE_VERSION = subprocess.check_output(["xmllint", "--format", "-"]).decode().strip()
    LOGOS_RELEASE_VERSION = subprocess.check_output(["sed", "-e", 's/ xmlns.*=".*"//g']).decode().strip()
    LOGOS_RELEASE_VERSION = subprocess.check_output(["sed", "-e", 's@logos:minimum-os-version@minimum-os-version@g']).decode().strip()
    LOGOS_RELEASE_VERSION = subprocess.check_output(["sed", "-e", 's@logos:version@version@g']).decode().strip()
    LOGOS_RELEASE_VERSION = subprocess.check_output(["xmllint", "--xpath", "/feed/entry[1]/version/text()", "-"]).decode().strip()
    export(LOGOS_RELEASE_VERSION)

    if LOGOS64_URL is None or LOGOS64_URL == "":
        LOGOS64_URL = f"https://downloads.logoscdn.com/LBS{TARGETVERSION}/{VERBUM_PATH}Installer/{LOGOS_RELEASE_VERSION}/{FLPRODUCT}-x64.msi"
        export(LOGOS64_URL)

    if FLPRODUCT == "Logos":
        LOGOS_VERSION = LOGOS64_URL.split('/')[6]
    elif FLPRODUCT == "Verbum":
        LOGOS_VERSION = LOGOS64_URL.split('/')[7]
    else:
        logos_error("FLPRODUCT not set in config. Please update your config to specify either 'Logos' or 'Verbum'.")
    export(LOGOS_VERSION)

    LOGOS64_MSI = os.path.basename(LOGOS64_URL)
    export(LOGOS64_MSI)
    
    if INSTALLDIR is None or INSTALLDIR == "":
        INSTALLDIR = f"{HOME}/{FLPRODUCT}Bible{TARGETVERSION}"
        export(INSTALLDIR)
    if APPDIR is None or APPDIR == "":
        APPDIR = f"{INSTALLDIR}/data"
        export(APPDIR)
    if APPDIR_BINDIR is None or APPDIR_BINDIR == "":
        APPDIR_BINDIR = f"{APPDIR}/bin"
        export(APPDIR_BINDIR)

def wineBinaryVersionCheck(TESTBINARY, TARGETVERSION):
    # Does not check for Staging. Will not implement: expecting merging of commits in time.
    if TARGETVERSION == "10":
        WINE_MINIMUM = "7.18"
    elif TARGETVERSION == "9":
        WINE_MINIMUM = "7.0"
    else:
        raise ValueError("TARGETVERSION not set.")

    # Check if the binary is executable. If so, check if TESTBINARY's version is ≥ WINE_MINIMUM, or if it is Proton or a link to a Proton binary, else remove.
    if os.path.exists(TESTBINARY) and os.access(TESTBINARY, os.X_OK):
        cmd = [TESTBINARY, "--version"]
        output = subprocess.check_output(cmd).decode("utf-8")
        TESTWINEVERSION = re.search(r"-\s([\d.]+)", output).group(1)
        TESTWINEVERSION = float(TESTWINEVERSION)
        if TESTWINEVERSION >= float(WINE_MINIMUM):
            if TESTWINEVERSION != 8.0:
                return True
        elif re.search("Proton - Experimental", TESTBINARY):
            return True
        # If it is a symlink, check its actual path. If it is Proton, let it pass.
        elif os.path.islink(TESTBINARY):
            TESTWINE = os.path.realpath(TESTBINARY)
            if re.search("Proton - Experimental", TESTWINE):
                return True
        else:
            return False
    
    return False

def checkPath(TESTBINARY):
    paths = os.environ["PATH"].split(":")
    for path in paths:
        binary_path = os.path.join(path, TESTBINARY)
        if os.path.exists(binary_path) and os.access(binary_path, os.X_OK):
            return binary_path
    
    return None

def createWineBinaryList():
    logos_info("Creating binary list.")
    # TODO: Make optarg to add custom path to this list.
    WineBinPathList = ["/usr/local/bin", os.path.expanduser("~") + "/bin",
                       os.path.expanduser("~") + "/PlayOnLinux/wine/linux-amd64/*/bin",
                       os.path.expanduser("~") + "/.steam/steam/steamapps/common/Proton - Experimental/files/bin",
                       CUSTOMBINPATH]

    # Temporarily modify PATH for additional WINE64 binaries.
    for p in WineBinPathList:
        if p not in os.environ['PATH'] and os.path.isdir(p):
            os.environ['PATH'] = os.environ['PATH'] + os.pathsep + p

    # Check each directory in PATH for wine64; add to list
    checkPath("wine64", WORKDIR + "/winebinaries")

    shutil.copy(WORKDIR + "/winebinaries", WORKDIR + "/winebinaries.bak")

    # Check remaining binary versions
    with open(WORKDIR + "/winebinaries.bak", "r") as file:
        lines = file.readlines()
        for line in lines:
            i = line.strip()
            if not wineBinaryVersionCheck(i):
                with open(WORKDIR + "/winebinaries", "r+") as file:
                    lines = file.readlines()
                    file.seek(0)
                    for line in lines:
                        if i not in line.strip():
                            file.write(line)
                    file.truncate()

def createWineBinaryList():
    # Add your implementation here
    pass

def no_diag_msg(msg):
    print(msg)

def chooseInstallMethod():

    if not os.environ.get("WINEPREFIX"):
        os.environ["WINEPREFIX"] = os.path.join(APPDIR, "wine64_bottle")

    if not os.environ.get("WINE_EXE"):
        createWineBinaryList()
        
        WINEBIN_OPTIONS = []
        
        # Add AppImage to list
        if TARGETVERSION != "9":
            if DIALOG == "whiptail" or DIALOG == "dialog":
                WINEBIN_OPTIONS.append("AppImage " + os.path.join(APPDIR_BINDIR, WINE64_APPIMAGE_FULL_FILENAME) + " AppImage of Wine64 " + WINE64_APPIMAGE_FULL_VERSION + " ON")
            elif DIALOG == "zenity":
                WINEBIN_OPTIONS.append("TRUE AppImage AppImage of Wine64 " + WINE64_APPIMAGE_FULL_VERSION + " " + os.path.join(APPDIR_BINDIR, WINE64_APPIMAGE_FULL_FILENAME))
            elif DIALOG == "kdialog":
                no_diag_msg("kdialog not implemented.")
            else:
                no_diag_msg("No dialog tool found.")
        
        while True:
            line = sys.stdin.readline().strip() # Read input from stdin
            if not line: break
            
            # Set binary code, description, and path based on path
            if os.path.islink(line):
                WINEOPT = os.path.realpath(line)
            else:
                WINEOPT = line

            if "/usr/bin/" in WINEOPT:
                WINEOPT_CODE = "System"
                WINEOPT_DESCRIPTION = "\"Use the system binary (i.e., /usr/bin/wine64). WINE must be 7.18-staging or later. Stable or Devel do not work.\""
                WINEOPT_PATH = line
            elif "Proton" in WINEOPT:
                WINEOPT_CODE = "Proton"
                WINEOPT_DESCRIPTION = "\"Install using the Steam Proton fork of WINE.\""
                WINEOPT_PATH = line
            elif "PlayOnLinux" in WINEOPT:
                WINEOPT_CODE = "PlayOnLinux"
                WINEOPT_DESCRIPTION = "\"Install using a PlayOnLinux WINE64 binary.\""
                WINEOPT_PATH = line
            else:
                WINEOPT_CODE = "Custom"
                WINEOPT_DESCRIPTION = "\"Use a WINE64 binary from another directory.\""
                WINEOPT_PATH = line

            # Create wine binary option array
            if DIALOG == "whiptail" or DIALOG == "dialog":
                WINEBIN_OPTIONS.append(WINEOPT_CODE + " " + WINEOPT_PATH + " " + WINEOPT_DESCRIPTION + " OFF")
            elif DIALOG == "zenity":
                WINEBIN_OPTIONS.append("FALSE " + WINEOPT_CODE + " " + WINEOPT_DESCRIPTION + " " + WINEOPT_PATH)
            elif DIALOG == "kdialog":
                no_diag_msg("kdialog not implemented.")
            else:
                no_diag_msg("No dialog tool found.")

        installArray = subprocess.check_output(["zenity", "--width=1024", "--height=480", "--title=" + TITLE, "--text=" + QUESTION_TEXT, "--list", "--radiolist"] + WINEBIN_OPTIONS + ["--print-column=2,3,4"]).decode().strip().split('|')

        WINEBIN_CODE = installArray[0]
        WINE_EXE = installArray[2]
    elif DIALOG == "zenity":
        column_names = ["--column", "Choice", "--column", "Code", "--column", "Description", "--column", "Path"]
        installationChoice = subprocess.check_output(["zenity", "--width=1024", "--height=480", "--title=" + TITLE, "--text=" + QUESTION_TEXT, "--list", "--radiolist"] + column_names + WINEBIN_OPTIONS + ["--print-column=2,3,4"]).decode().strip()
        installArray = installationChoice.split('|')
        WINEBIN_CODE = installArray[0]
        WINE_EXE = installArray[2]
    elif DIALOG == "kdialog":
        no_diag_msg("kdialog not implemented.")
    else:
        no_diag_msg("No dialog tool found.")

    verbose()
    print(f"chooseInstallMethod(): WINEBIN_CODE: {WINEBIN_CODE}; WINE_EXE: {WINE_EXE}")

def checkExistingInstall():
    # Now that we know what the user wants to install and where, determine whether an install exists and whether to continue.
    if os.path.isdir(INSTALLDIR):
        if any(os.path.isfile(os.path.join(INSTALLDIR, file)) for file in ['Logos.exe', 'Verbum.exe']):
            global EXISTING_LOGOS_INSTALL
            EXISTING_LOGOS_INSTALL = 1
            print(f"An install was found at {INSTALLDIR}. Please remove/rename it or use another location by setting the INSTALLDIR variable.")
        else:
            global EXISTING_LOGOS_DIRECTORY
            EXISTING_LOGOS_DIRECTORY = 1
            print(f"A directory exists at {INSTALLDIR}. Please remove/rename it or use another location by setting the INSTALLDIR variable.")
    else:
        if verbose:
            print(f"Installing to an empty directory at {INSTALLDIR}.")


def beginInstall():
    if SKEL == "1":
        if verbose:
            print("Making a skeleton install of the project only. Exiting after completion.")
        make_skel("none.AppImage")
        exit(0)

    if WINEBIN_CODE:
        if WINEBIN_CODE.startswith("AppImage"):
            check_libs("libfuse")
            if verbose:
                print(f"Installing {FLPRODUCT} Bible {TARGETVERSION} using {WINE64_APPIMAGE_FULL_VERSION} AppImage…")
            if not REGENERATE:
                make_skel(WINE64_APPIMAGE_FULL_FILENAME)
                # exporting PATH to internal use if using AppImage, doing backup too:
                os.environ["OLD_PATH"] = os.environ["PATH"]
                os.environ["PATH"] = f"{APPDIR_BINDIR}:{os.environ['PATH']}"
                # Geting the AppImage:
                getAppImage()
                os.chmod(f"{APPDIR_BINDIR}/{WINE64_APPIMAGE_FULL_FILENAME}", 0o755)
                os.environ["WINE_EXE"] = f"{APPDIR_BINDIR}/wine64"
        elif WINEBIN_CODE in ["System", "Proton", "PlayOnLinux", "Custom"]:
            if verbose:
                print(f"Installing {FLPRODUCT} Bible {TARGETVERSION} using a {WINEBIN_CODE} WINE64 binary…")
            if not REGENERATE:
                make_skel("none.AppImage")
        else:
            print("WINEBIN_CODE error. Installation canceled!")
            sys.exit(1)
    else:
        if verbose:
            print("WINEBIN_CODE is not set in your config file.")

    if verbose:
        wine_version = subprocess.check_output([WINE_EXE, "--version"]).decode().strip()
        print(f"Using: {wine_version}")

    # Set WINESERVER_EXE based on WINE_EXE.
    if not WINESERVER_EXE:
        wineserver_path = os.path.join(os.path.dirname(WINE_EXE), "wineserver")
        if os.path.exists(wineserver_path):
            WINESERVER_EXE = wineserver_path
        else:
            print(f"{wineserver_path} not found. Please either add it or create a symlink to it, and rerun.")

def prepareWineBottle():
    logos_continue_question("Now the script will create and configure the Wine Bottle at {}. You can cancel the installation of Mono. Do you wish to continue?".format(WINEPREFIX), "The installation was cancelled!")
    verboseCode()
    if not WINEBOOT_GUI:
        subprocess.Popen(["DISPLAY=","wineboot"], stdout=subprocess.PIPE).communicate()
    else:
        subprocess.Popen(["wineboot"], stdout=subprocess.PIPE).communicate()
    light_wineserver_wait()

def wine_reg_install(REG_FILENAME):
    verboseCode()
    subprocess.Popen(["regedit.exe", REG_FILENAME], cwd=WORKDIR).communicate()
    light_wineserver_wait()
    verboseCode()
    
def downloadWinetricks():
    logos_reuse_download(WINETRICKS_URL, "winetricks", APPDIR_BINDIR)
    subprocess.Popen(["chmod", "755" "{}/winetricks".format(APPDIR_BINDIR)], stdout=subprocess.PIPE).communicate()

def setWinetricks():
    # Check if local winetricks version available; else, download it
    if not "WINETRICKSBIN" in os.environ:
        if subprocess.call(["which", "winetricks"]) == 0:
            # Check if local winetricks version is up-to-date; if so, offer to use it or to download; else, download it
            local_winetricks_version = subprocess.check_output(["winetricks", "--version"]).split()[0]
            if local_winetricks_version >= "20220411":
                backtitle = "Choose Winetricks Menu"
                title = "Choose Winetricks"
                question_text = "Should the script use the system's local winetricks or download the latest winetricks from the Internet? The script needs to set some Wine options that FLPRODUCT requires on Linux."
                if os.getenv("DIALOG") == "whiptail" or os.getenv("DIALOG") == "dialog":
                    dialog_choice = subprocess.Popen(
                        [os.getenv("DIALOG"), "--backtitle", backtitle, "--title", title, "--radiolist", question_text, "0", "0", "0", "1", "Use local winetricks.", "ON", "2", "Download winetricks from the Internet."], 
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    winetricks_choice = dialog_choice.communicate()[0]
                elif os.getenv("DIALOG") == "zenity":
                    dialog_choice = subprocess.Popen(
                        ["zenity", "--width=700", "--height=310", "--title=" + title, "--text=" + question_text, "--list", "--radiolist", "--column", "S", "--column", "Description", "TRUE", "1- Use local winetricks.", "FALSE", "2- Download winetricks from the Internet."], 
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    winetricks_choice = dialog_choice.communicate()[0]
                elif os.getenv("DIALOG") == "kdialog":
                    sys.exit("kdialog not implemented.")
                else:
                    sys.exit("No dialog tool found.")

                if winetricks_choice.startswith(b"1"):
                    print("Setting winetricks to the local binary...")
                    os.environ["WINETRICKSBIN"] = subprocess.check_output(["which", "winetricks"]).strip()
                elif winetricks_choice.startswith(b"2"):
                    downloadWinetricks()
                    os.environ["WINETRICKSBIN"] = os.path.join(os.getenv("APPDIR_BINDIR"), "winetricks")
                else:
                    sys.exit("Installation canceled!")
            else:
                print("The system's winetricks is too old. Downloading an up-to-date winetricks from the Internet...")
                downloadWinetricks()
                os.environ["WINETRICKSBIN"] = os.path.join(os.getenv("APPDIR_BINDIR"), "winetricks")
        else:
            print("Local winetricks not found. Downloading winetricks from the Internet...")
            downloadWinetricks()
            os.environ["WINETRICKSBIN"] = os.path.join(os.getenv("APPDIR_BINDIR"), "winetricks")

    print("Winetricks is ready to be used.")

def winetricks_install(*args):
    verbose and print("winetricks", *args)
    if DIALOG == "whiptail" or DIALOG == "dialog":
        subprocess.call([WINETRICKSBIN, *args])
    elif DIALOG == "zenity":
        pipe_winetricks = tempfile.mktemp()
        os.mkfifo(pipe_winetricks)

        # zenity GUI feedback
        logos_progress("Winetricks " + " ".join(args), "Winetricks installing " + " ".join(args), input=open(pipe_winetricks))

        proc = subprocess.Popen([WINETRICKSBIN, *args], stdout=subprocess.PIPE)
        with open(pipe_winetricks, "w") as pipe:
            for line in proc.stdout:
                pipe.write(line)
                print(line.decode(), end="")

        WINETRICKS_STATUS = proc.wait()
        ZENITY_RETURN = proc.poll()

        os.remove(pipe_winetricks)

        # NOTE: sometimes the process finishes before the wait command, giving the error code 127
        if ZENITY_RETURN == 0 or ZENITY_RETURN == 127:
            if WINETRICKS_STATUS != 0:
                subprocess.call([WINESERVER_EXE, "-k"])
                logos_error("Winetricks Install ERROR: The installation was cancelled because of sub-job failure!\n * winetricks " + " ".join(args) + "\n  - WINETRICKS_STATUS: " + str(WINETRICKS_STATUS))
        else:
            subprocess.call([WINESERVER_EXE, "-k"])
            logos_error("The installation was cancelled!\n * ZENITY_RETURN: " + str(ZENITY_RETURN))
    elif DIALOG == "kdialog":
        no_diag_msg("kdialog not implemented.")
    else:
        no_diag_msg("No dialog tool found.")

    verbose and print("winetricks", *args, "DONE!")

    heavy_wineserver_wait()

def winetricks_dll_install(*args):
    verbose and print("winetricks", *args)
    logos_continue_question("Now the script will install the DLL " + " ".join(args) + ". This may take a while. There will not be any GUI feedback for this. Continue?", "The installation was cancelled!")
    subprocess.call([WINETRICKSBIN, *args])
    verbose and print("winetricks", *args, "DONE!")
    heavy_wineserver_wait()

def getPremadeWineBottle():
    verbose and print("Installing pre-made wineBottle 64bits…")
    logos_reuse_download(WINE64_BOTTLE_TARGZ_URL, WINE64_BOTTLE_TARGZ_NAME, WORKDIR)
    subprocess.call(["tar", "xzf", os.path.join(WORKDIR, WINE64_BOTTLE_TARGZ_NAME), "-C", APPDIR])
    logos_progress("Extracting…", "Extracting: " + WINE64_BOTTLE_TARGZ_NAME + "\ninto: " + APPDIR)

## END WINE BOTTLE AND WINETRICKS FUNCTIONS
## BEGIN LOGOS INSTALL FUNCTIONS
def get_logos_executable():
    # This VAR is used to verify the downloaded MSI is latest
    if not LOGOS_EXECUTABLE:
        LOGOS_EXECUTABLE = f"{FLPRODUCT}_v{LOGOS_VERSION}-x64.msi"
    
    logos_continue_question("Now the script will check for the MSI installer. Then it will download and install {FLPRODUCT} Bible at {WINEPREFIX}. You will need to interact with the installer. Do you wish to continue?", "The installation was cancelled!")
    
    # Getting and installing {FLPRODUCT} Bible
    # First check current directory to see if the .MSI is present; if not, check user's Downloads/; if not, download it new. Once found, copy it to WORKDIR for future use.
    verbose() and print(f"Installing {FLPRODUCT}Bible 64bits…")
    if os.path.isfile(f"{PRESENT_WORKING_DIRECTORY}/{LOGOS_EXECUTABLE}"):
        verbose() and print(f"{LOGOS_EXECUTABLE} exists. Using it…")
        shutil.copy(f"{PRESENT_WORKING_DIRECTORY}/{LOGOS_EXECUTABLE}", f"{APPDIR}/")
    elif os.path.isfile(f"{HOME}/Downloads/{LOGOS_EXECUTABLE}"):
        verbose() and print(f"{LOGOS_EXECUTABLE} exists. Using it…")
        shutil.copy(f"{HOME}/Downloads/{LOGOS_EXECUTABLE}", f"{APPDIR}/")
    else:
        verbose() and print(f"{LOGOS_EXECUTABLE} does not exist. Downloading…")
        logos_download(LOGOS64_URL, f"{HOME}/Downloads/")
        shutil.move(f"{HOME}/Downloads/{LOGOS64_MSI}", f"{HOME}/Downloads/{LOGOS_EXECUTABLE}")
        shutil.copy(f"{HOME}/Downloads/{LOGOS_EXECUTABLE}", f"{APPDIR}/")
        
def install_msi():
    # Execute the .MSI
    verbose() and print(f"Running: {WINE_EXE} msiexec /i {APPDIR}/{LOGOS_EXECUTABLE}")
    subprocess.run([WINE_EXE, "msiexec", "/i", f"{APPDIR}/{LOGOS_EXECUTABLE}"])

def installFonts():
    if os.environ.get('WINETRICKS_UNATTENDED') is None:
        if os.environ.get('SKIP_FONTS') is None:
            winetricks_install('-q', 'corefonts')
            winetricks_install('-q', 'tahoma')
    else:
        if os.environ.get('SKIP_FONTS') is None:
            winetricks_install('corefonts')
            winetricks_install('tahoma')
    winetricks_install('-q', 'settings', 'fontsmooth=rgb')

def installD3DCompiler():
    if os.environ.get('WINETRICKS_UNATTENDED') is None:
        winetricks_dll_install('-q', 'd3dcompiler_47')
    else:
        winetricks_dll_install('d3dcompiler_47')

def installLogos9():
    getPremadeWineBottle()
    setWinetricks()
    installFonts()
    installD3DCompiler()
    getLogosExecutable()
    installMSI()

    if verbose():
        print("======= Set {}Bible Indexing to Vista Mode: =======".format(FLPRODUCT))
    os.system('{} reg add "HKCU\\Software\\Wine\\AppDefaults\\{}Indexer.exe" /v Version /t REG_SZ /d vista /f'.format(WINE_EXE, FLPRODUCT))
    if verbose():
        print("======= {}Bible logging set to Vista mode! =======".format(FLPRODUCT))

def installLogos10():
    with open(os.path.join(WORKDIR, 'disable-winemenubuilder.reg'), 'w') as reg_file, \
            open(os.path.join(WORKDIR, 'renderer_gdi.reg'), 'w') as gdi_file:
        reg_file.write('''REGEDIT4

[HKEY_CURRENT_USER\Software\Wine\Direct3D]
"DirectDrawRenderer"="gdi"
"renderer"="gdi"
''')
        gdi_file.write('''REGEDIT4

[HKEY_CURRENT_USER\Software\Wine\Direct3D]
"DirectDrawRenderer"="gdi"
"renderer"="gdi"
''')

    wine_reg_install("disable-winemenubuilder.reg")
    wine_reg_install("renderer_gdi.reg")

    setWinetricks()
    installFonts()
    installD3DCompiler()

    if not WINETRICKS_UNATTENDED:
        winetricks_install("-q settings win10")
    else:
        winetricks_install("settings win10")

    getLogosExecutable()
    installMSI()

def getScriptTemplate(script_template):
    SCRIPT_TEMPLATE = script_template
    if SCRIPT_TEMPLATE == "Launcher-Template.sh":
        SCRIPT_TEMPLATE_URL = LAUNCHER_TEMPLATE_URL
    else:
        SCRIPT_TEMPLATE_URL = CONTROL_PANEL_TEMPLATE_URL

    verbose()
    print("Downloading the launcher script template…")

    if os.path.isfile(os.path.join(PRESENT_WORKING_DIRECTORY, SCRIPT_TEMPLATE)):
        verbose()
        print(f"{SCRIPT_TEMPLATE} found. Using it…")
        shutil.copy(os.path.join(PRESENT_WORKING_DIRECTORY, SCRIPT_TEMPLATE), os.path.join(WORKDIR, SCRIPT_TEMPLATE))
    elif os.path.isfile(os.path.join(HOME, 'Downloads', SCRIPT_TEMPLATE)):
        verbose()
        print(f"{SCRIPT_TEMPLATE} found in Downloads. Replacing it…")
        os.remove(os.path.join(HOME, 'Downloads', SCRIPT_TEMPLATE))
        logos_download(SCRIPT_TEMPLATE_URL, os.path.join(HOME, 'Downloads'))
        shutil.copy(os.path.join(HOME, 'Downloads', SCRIPT_TEMPLATE), os.path.join(WORKDIR, SCRIPT_TEMPLATE))
    else:
        logos_download(SCRIPT_TEMPLATE_URL, os.path.join(HOME, 'Downloads'))
        shutil.copy(os.path.join(HOME, 'Downloads', SCRIPT_TEMPLATE), os.path.join(WORKDIR, SCRIPT_TEMPLATE))

def apply_shell_expansion(file):
    data = os.system(f"{WORKDIR}/{FLPRODUCT}.sh")
    os.chmod(f"{WORKDIR}/{FLPRODUCT}.sh", 755)
    os.rename(f"{WORKDIR}/{FLPRODUCT}.sh", f"{INSTALLDIR}/")

def createControlPanel():
    getScriptTemplate("controlPanel-Template.sh")
    with open(f"{WORKDIR}/controlPanel-Template.sh") as template_file:
        template_data = template_file.read()
    expanded_data = apply_shell_expansion(f"{WORKDIR}/controlPanel-Template.sh")
    with open(f"{WORKDIR}/controlPanel.sh", "w") as control_panel_file:
        control_panel_file.write(expanded_data)
    os.chmod(f"{WORKDIR}/controlPanel.sh", 755)
    os.rename(f"{WORKDIR}/controlPanel.sh", f"{INSTALLDIR}/")

def create_starting_scripts():
    if verbose:
        print(f"Creating starting scripts for {FLPRODUCT}Bible 64 bits...")
    createLauncher()
    createControlPanel()

def createConfig():
    config_data = '''\
        # INSTALL OPTIONS
        FLPRODUCT="{FLPRODUCT}"
        FLPRODUCTi="{FLPRODUCTi}"
        TARGETVERSION="{TARGETVERSION}"
        INSTALLDIR="{INSTALLDIR}"
        APPDIR="{APPDIR}"
        APPDIR_BINDIR="{APPDIR_BINDIR}"
        WINETRICKSBIN="{WINETRICKSBIN}"
        WINEPREFIX="{WINEPREFIX}"
        WINEBIN_CODE="{WINEBIN_CODE}"
        WINE_EXE="{WINE_EXE}"
        WINESERVER_EXE="{WINESERVER_EXE}"
        WINE64_APPIMAGE_FULL_URL="{WINE64_APPIMAGE_FULL_URL}"
        WINE64_APPIMAGE_FULL_FILENAME="{WINE64_APPIMAGE_FULL_FILENAME}"
        APPIMAGE_LINK_SELECTION_NAME="{APPIMAGE_LINK_SELECTION_NAME}"
        LOGOS_EXECUTABLE="{LOGOS_EXECUTABLE}"
        LOGOS_EXE="{LOGOS_EXE}"
        LOGOS_DIR="{LOGOS_DIR}"

        # RUN OPTIONS
        LOGS="DISABLED"

        # RESTORE OPTIONS
        BACKUPDIR=""
    '''
    with open(f"{HOME}/.config/Logos_on_Linux/Logos_on_Linux.conf", "w") as config_file:
        config_file.write(config_data)

def postInstall():
    if os.path.isfile(LOGOS_EXE):
        logos_info(f"{FLPRODUCT} Bible {TARGETVERSION} installed!")
        if not LOGOS_CONFIG and not os.path.isfile(DEFAULT_CONFIG_PATH):
            os.makedirs(os.path.join(HOME, ".config", "Logos_on_Linux"), exist_ok=True)
            if os.path.isdir(os.path.join(HOME, ".config", "Logos_on_Linux")):
                createConfig()
                logos_info(f"A config file was created at {DEFAULT_CONFIG_PATH}.")
            else:
                logos_warn(f"{HOME}/.config/Logos_on_Linux does not exist. Failed to create config file.")
        elif not LOGOS_CONFIG and os.path.isfile(DEFAULT_CONFIG_PATH):
            if logos_acknowledge_question(f"The script found a config file at {DEFAULT_CONFIG_PATH}. Should the script overwrite the existing config?", "The existing config file was not overwritten."):
                if os.path.isdir(os.path.join(HOME, ".config", "Logos_on_Linux")):
                    createConfig()
                else:
                    logos_warn(f"{HOME}/.config/Logos_on_Linux does not exist. Failed to create config file.")
        else:
            # Script was run with a config file. Skip modifying the config.
            pass

        if logos_acknowledge_question("A launch script has been placed in {INSTALLDIR} for your use. The script's name is {FLPRODUCT}.sh.\nDo you want to run it now?\nNOTE: There may be an error on first execution. You can close the error dialog.", "The Script has finished. Exiting…"):
            subprocess.run([os.path.join(INSTALLDIR, f"{FLPRODUCT}.sh")])
        elif verbose:
            print("The script has finished. Exiting…")
    else:
        logos_error("Installation failed. {LOGOS_EXE} not found. Exiting…\nThe {FLPRODUCT} executable was not found. This means something went wrong while installing {FLPRODUCT}. Please contact the Logos on Linux community for help.")

def main():
    print(f"{os.environ.get('LOGOS_SCRIPT_TITLE')}, {os.environ.get('LOGOS_SCRIPT_VERSION')} by {os.environ.get('LOGOS_SCRIPT_AUTHOR')}.")
    # BEGIN PREPARATION
    if verbose:
        print(datetime.datetime.now())
    checkDependencies()  # We verify the user is running a graphical UI and has majority of required dependencies.
    if verbose:
        print(datetime.datetime.now())
    chooseProduct()  # We ask user for his Faithlife product's name and set variables.
    if verbose:
        print(datetime.datetime.now())
    chooseVersion()  # We ask user for his Faithlife product's version, set variables, and create project skeleton.
    if verbose:
        print(datetime.datetime.now())
    chooseInstallMethod()  # We ask user for his desired install method.
    # END PREPARATION
    
    if not REGENERATE:
        if verbose:
            print(datetime.datetime.now())
        checkExistingInstall()
        if verbose:
            print(datetime.datetime.now())
        beginInstall()
        if verbose:
            print(datetime.datetime.now())
        prepareWineBottle()  # We run wineboot.
        
        if TARGETVERSION.startswith("10"):
            if verbose:
                print(datetime.datetime.now())
            installLogos10()  # We run the commands specific to Logos 10.
        elif TARGETVERSION.startswith("9"):
            if verbose:
                print(datetime.datetime.now())
            installLogos9()  # We run the commands specific to Logos 9.
        else:
            logos_error("Installation canceled!")
        
        if verbose:
            print(datetime.datetime.now())
        create_starting_scripts()
        heavy_wineserver_wait()
        clean_all()
        
        LOGOS_EXE = subprocess.run(["find", WINEPREFIX, "-name", f"{FLPRODUCT}.exe"], capture_output=True, text=True).stdout.strip()
        os.environ["LOGOS_EXE"] = LOGOS_EXE
        
        if verbose:
            print(datetime.datetime.now())
        postInstall()
    else:
        create_starting_scripts()
        logos_info("The scripts have been regenerated.")
    
    with open(LOGOS_LOG, "a") as f:
        f.write(output)

# END FUNCTION DECLARATIONS

# BEGIN SCRIPT EXECUTION
if not os.environ.get("DIALOG"):
    getDialog()
    if os.environ.get("GUI") == "true":
        with open(LOGOS_LOG, "a") as f:
            f.write("Running in a GUI. Enabling logging.\n")
        setDebug()

die_if_running()
die_if_root()

# BEGIN OPTARGS
RESET_OPTARGS = True
args = sys.argv[1:]
while args:
    if RESET_OPTARGS:
        RESET_OPTARGS = False
        args = []
    arg = args.pop(0)
    if arg == "--help":
        args.extend(["-h"])
    elif arg == "--version":
        args.extend(["-v"])
    elif arg == "--verbose":
        args.extend(["-V"])
    elif arg == "--config":
        args.extend(["-c"])
    elif arg == "--skip-fonts":
        args.extend(["-F"])
    elif arg == "--regenerate-scripts":
        args.extend(["-r"])
    elif arg == "--force-root":
        args.extend(["-f"])
    elif arg == "--debug":
        args.extend(["-D"])
    elif arg == "--make-skel":
        args.extend(["-k"])
    elif arg == "--custom-binary-path":
        args.extend(["-b"])
    else:
        args.append(arg)
OPTSTRING = ":hvVcDfFrkb:"  # Available options

# First loop: set variable options which may affect other options
while args:
    opt = args.pop(0)
    if opt == "-c":
        if args:
            next_arg = args.pop(0)
            if next_arg and not next_arg.startswith("-"):
                if os.path.isfile(next_arg):
                    LOGOS_CONFIG = next_arg
                    os.environ["LOGOS_CONFIG"] = LOGOS_CONFIG
                    with open(LOGOS_CONFIG) as f:
                        code = compile(f.read(), LOGOS_CONFIG, 'exec')
                        exec(code, globals())
                else:
                    sys.stderr.write(f"{LOGOS_SCRIPT_TITLE}: -c: Invalid config file path.\n")
                    usage()
                    sys.exit()
            else:
                if os.path.isfile(os.path.expanduser("~/.config/Logos_on_Linux/Logos_on_Linux.conf")):
                    LOGOS_CONFIG = os.path.expanduser("~/.config/Logos_on_Linux/Logos_on_Linux.conf")
                    os.environ["LOGOS_CONFIG"] = LOGOS_CONFIG
                    with open(LOGOS_CONFIG) as f:
                        code = compile(f.read(), LOGOS_CONFIG, 'exec')
                        exec(code, globals())
                else:
                    sys.stderr.write("No config file found.\n")
    elif opt == "-V":
        os.environ["VERBOSE"] = "true"
    elif opt == "-F":
        os.environ["SKIP_FONTS"] = "1"
    elif opt == "-f":
        os.environ["LOGOS_FORCE_ROOT"] = "1"
    elif opt == "-r":
        os.environ["REGENERATE"] = "1"
    elif opt == "-D":
        setDebug()
    elif opt == "-k":
        os.environ["SKEL"] = "1"
    elif opt == "-b":
        if args:
            CUSTOMBINPATH = args.pop(0)
            if os.path.isdir(CUSTOMBINPATH):
                os.environ["CUSTOMBINPATH"] = CUSTOMBINPATH
            else:
                sys.stderr.write(f"{LOGOS_SCRIPT_TITLE}: User supplied path: \"{CUSTOMBINPATH}\". Custom binary path does not exist.\n")
                usage()
                sys.exit()
        else:
            sys.stderr.write(f"{LOGOS_SCRIPT_TITLE}: -b: missing argument.\n")
            usage()
            sys.exit()
    elif opt == "-h":
        usage()
        sys.exit()
    elif opt == "-v":
        sys.stdout.write(f"{LOGOS_SCRIPT_TITLE}, {LOGOS_SCRIPT_VERSION} by {LOGOS_SCRIPT_AUTHOR}.\n")
        sys.exit()
    else:
        sys.stderr.write(f"{LOGOS_SCRIPT_TITLE}: {opt}: undefined option.\n")
        usage()
        sys.exit()

OPTIND = 1  # Reset the index.

# Second loop: determine user action
args = sys.argv[1:]
while args:
    opt = args.pop(0)
    if opt == "-h":
        usage()
        sys.exit()
    elif opt == "-v":
        sys.stdout.write(f"{LOGOS_SCRIPT_TITLE}, {LOGOS_SCRIPT_VERSION} by {LOGOS_SCRIPT_AUTHOR}.\n")
        sys.exit()
    elif opt == "-?":
        sys.stderr.write(f"{LOGOS_SCRIPT_TITLE}: {opt}: undefined option.\n")
        usage()
        sys.exit()
    elif opt == ":":
        sys.stderr.write(f"{LOGOS_SCRIPT_TITLE}: {opt}: missing argument.\n")
        usage()
        sys.exit()

# If no options passed.
if len(sys.argv) == 1:
    pass

args = sys.argv[1:]
main()

sys.exit(0)
# END SCRIPT EXECUTION

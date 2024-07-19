#!/bin/bash
# Setup script for the PhenoHive project
# This script installs the necessary packages and enables the SPI interface on the Raspberry Pi
# It also sets up the PhenoHive service to run on boot
# It is intended to be run on a fresh install on a Debian Linux Distribution (Raspbian or DietPi)

LOG_FILE="logs/phenoHive_setup_$(date +%Y-%m-%d_%H-%M-%S).log"
touch "$LOG_FILE"
CONFIG_FILE="tools/setup.config"

# Redirect output to both the log file and stdout with timestamps
exec > >(awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0; fflush(); }' | tee -a "$LOG_FILE") 2>&1

# Color codes for the outputs
ERROR='\033[0;31m'
INFO='\033[0;36m'
WHITE='\033[0m'

log() {
    # Redirect output to both a log file and stdout
    echo -e "$(date) - $1" >> $LOG_FILE
}

check_internet() {
    if ! ping -q -c 1 -W 1 google.com &> /dev/null; then
        log "${ERROR}Please ensure that the Raspberry Pi is connected to the internet before running this script.${WHITE}"
        exit 1
    fi
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log "${ERROR}Please run as root: sudo bash setup.sh${WHITE}"
        exit 1
    fi
}

check_directory() {
  # Check if the script is being run from the correct directory
    if [ -f $CONFIG_FILE ]; then
        cd ..
        if [ ! -f main.py ]; then
            log "${ERROR}Please run the script from the PhenoHive directory. Current directory: $(pwd)${WHITE}"
            exit 1
        fi
    else
        log "${ERROR}Please run the script from the PhenoHive directory. Current directory: $(pwd)${WHITE}"
        exit 1
    fi
}

install_packages() {
    log "${INFO}Installing necessary packages...${WHITE}"
    # Check if running on DietPi, if so, remove apt compression
    if [ -f /boot/dietpi/.dietpi ]; then
        # Remove apt compression to speed up the process
        echo 'Acquire::GzipIndexes "false";' > /etc/apt/apt.conf.d/98dietpi-uncompressed
        /boot/dietpi/func/dietpi-set_software apt-cache clean
    fi
    if ! apt-get update; then
        log "${ERROR}Failed to update package list. Exiting.${WHITE}"
        exit 1
    fi
    if ! grep -vE '^\s*#' $CONFIG_FILE | xargs apt-get -y install; then
        log "${ERROR}Failed to install packages. Exiting.${WHITE}"
        exit 1
    fi
}

install_python_packages() {
    log "${INFO}Installing necessary Python packages...${WHITE}"
    if ! pip install -r requirements.txt --break-system-packages --root-user-action=ignore --no-cache-dir; then
        log "${ERROR}Failed to install Python packages. Exiting.${WHITE}"
        exit 1
    fi
}

install_st7735() {
    log "${INFO}Installing ST7735 library...${WHITE}"
    git clone https://github.com/degzero/Python_ST7735.git >> /dev/null 2>&1
    cd Python_ST7735 || log "${ERROR}Python_ST335 could not be installed: Could not find directory.${WHITE}"
    python setup.py install
    cd ..
}

enable_spi() {
    log "${INFO}Enabling SPI interface...${WHITE}"
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        if [[ $ID != "raspbian" ]]; then
            # On a raspbian system, use raspi-config to enable SPI
            raspi-config nonint do_spi 0
        else
            # On a dietpi or other non-raspbian system, enable the SPI interface in the config file
            echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
        fi
    fi
}

setup_service() {
    log "${INFO}Setting up PhenoHive service...${WHITE}"
    # Modify the WorkingDirectory and ExecStart in the service file to point to the correct (current) directory
    PROJECT_DIR=$(pwd)
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=${PROJECT_DIR}|" tools/phenoHive.service
    sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python ${PROJECT_DIR}/main.py|" /etc/systemd/system/phenoHive.service
    cp tools/phenoHive.service /etc/systemd/system
    chmod 644 /etc/systemd/system/phenoHive.service
    chmod +x main.py
    systemctl daemon-reload
    systemctl enable phenoHive.service
}

log "${INFO}PhenoHive setup script.\n" \
    "\t This script installs the necessary packages and enables the SPI interface.\n" \
    "\t It also sets up the PhenoHive service to run on boot.\n" \
    "\t It is intended to be run on a fresh install of a Debian Linux Distribution (DietPi or Raspbian) running on a Raspberry Pi Zero W.${WHITE}"

log "${INFO}Running pre-setup checks...${WHITE}"
check_internet
check_root
check_directory

# Install required packages
install_packages
install_python_packages
install_st7735

# Enable spi interface (should be enabled by default)
enable_spi
# Setup PhenoHive as a service so PhenoHive/main.py is run on boot
setup_service

# Setup complete, reboot the Raspberry Pi
log "${INFO}Setup complete. A reboot is required before running the service.${WHITE}"

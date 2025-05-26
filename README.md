

# Movella DOT Recorder

This repository is aimed to sampling data from **Movella DOT** sensors. Using the Movella DOT PC SDK it is possible to configure, synchronize, sampling (logging), and visualize data in real-time (Roll, Pitch, Yaw of each Movella DOT sensor).

---

## REQUIREMENTS

- Operative System: Ubuntu 22.04 LTS 64-bit

- Install a Python version between 3.7.4 and 3.10.12 (Version 3.10.12 was used for development.)

- Install and extract the Movella SDK from this link

	 https://www.movella.com/supportsoftware-documentationhsCtaTracking=39d661fa-2ea8-4478-955e-01d0d8885f14%7C3ad1c7d6-9c3a-42e9-b424-5b15b9d0924e

- (option) Some command may not work properly. Run this command:

        sudo apt update && sudo apt upgrade -y

---

## INSTALLATION

1. create a virtual enviroment with the command:

	python3 -m venv nome_ambiente

a) if a virtual environment is not created, run this command:

	  sudo apt update
	  sudo apt install python3-venv

2. activate virtual enviroment, run this command:

    source enviroment/bin/activate

3. once in the virtual environment, install the movelladotpcsdk_linux-x64_2023.6.sh file located in the SDK folder installed at the beginning and run the command:

        sudo “PATH/Movella DOT SDK_Linux/movelladot_pc_sdk_linux-x64_2023.6_b345_r124108/movelladot_pc_sdk_linux-x64_2023.6/movelladotpcsdk_linux-x64_2023.6.sh"

	a) the error “ 'uudecode' could not be found. It is usually installed with the 'sharutils' package” could appear, allora eseguire il comando:
    
        sudo apt update && sudo apt install sharutils -y

	b) an installation folder will be asked, if you press the enter key without entering anything it will be installed in the default folder

	c) If the installation was successful, a message similar to this should appear:
	  
            #8-Ubuntu SMP PREEMPT_DYNAMIC Mon Sep 16 13:41:20 UTC 2024 Start using by 	  adding -L/usr/local/movella to your linker options Or register systemwide using 	  	  ldconfig /usr/local/movella

4. the Movella SDK installation guide suggest running this command:

        sudo apt-get install build-essential curl cmake libgfortran4 libxcb-xkb-dev libcurl4-openssl-dev libbluetooth-dev 

    but this version is no longer available, so use the commands instead:

        sudo apt-get install libgfortran5
        sudo apt-get install build-essential curl cmake libgfortran5 libxcb-xkb-dev libcurl4-openssl-dev libbluetooth-dev

5. move inside the folder where the sdk was downloaded and then into the python folder; these are the .whl files that you need to install. Run the command to install the .whl corresponding to the version of python used (in our case Python 3.10)

    pip install movelladot_pc_sdk-2023.6.0-cp310-none-linux_x86_64.whl

6. move to the /examples/xdpcsdk/python folder, here you can run the examples.

	a) It is recommended to run the command: 
    
        pip install -r requirements.txt


	b) for better compatibility between libraries and sdk is recommend installing these versions of pynput and numpy, run these commands:

	    pip install numpy==1.24.0
	    pip install pynput==1.7.3
---
## PARAMETERS

| Parameter        | Possible values                                                                                                                                                       | Description                                                    |
|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| `filter_profile` | `General`, `Dynamic`                                                                                                                                                   | Filter profile to apply                                   |
| `payload_mode`   | `custom1`, `custom2`, `custom3`, `custom4`, `custom5`,<br>`orientQuat`, `completeQuat`, `extQuat`,<br>`orientEul`, `completeEul`, `extEul`,<br>`freeAcc`,<br>`highFid`, `highFidMag`,<br>`dq`, `dqMag`,<br>`rq`, `rqMag`,<br>`mfm` | Data Payload Mode,                                   |
| `duration`       | Integer ≥ 1 or omit for indefinite                                                                                                                                      | 	Recording duration (seconds)
| `output_rate`    | `1`, `4`, `10`, `12`, `15`, `20`, `30`, `60`, `120`                                                                                                                     | Output rate (Hz)
| `show`           | `show`, `noshow`                                                                                                                                                       | Show orientation (Roll, Pitch, Yaw) in real-time |

---
## EXAMPLES 
Running the script via command line with finite duration

    python3 registration.py <filter_profile> <payload_mode> <duration> <output_rate> [show|noshow]

    python3 registration.py --filter_profile General --payload_mode custom4 --duration 10 --output_rate 30 --show show

Run with indefinite duration (recording stops after pressing ENTER)

    python3 registration.py --filter_profile General --payload_mode custom4 --output_rate 30 --show show

Running the script via GUI

    python3 gui.py

---

## IMPLEMENTED FEATURES

- Command line parameter parsing
- Initialization and connection to Movella DOT devices via Bluetooth
- Configuration of filter, output rate and logging options
- Automatic creation of `logs/` folder and CSV file with name `<device>_<timestamp>.csv`
- Logging to CSV file in background
- Multi-sensor synchronization (automatic retry, skip if only one device is connected)
- Start and stop the measurement, disable logging at the end
- Live display of Roll, Pitch and Yaw during recording (`show`)
- Support for indefinite duration (stop via ENTER in CLI or Stop in GUI)
- Interactive loop to repeat or change parameters without restarting the script 
- Heading reset and resource cleaning guaranteed in every condition (try/finally)

---

## INTERACTIVE MODE(CLI ONLY)

during the execution of registration.py script, at the end of each recording cycle, the script prompts the user:

- **`r`** → Repeat the recording with the same parameters
- **`m`** → Edit interactively
    - `payload_mode`
    - `duration`
    - `output_rate`
    - `show` / `noshow`
    - optionally keep a certain variable at its previous value simply by pressing the `enter` key
- **`q`** → Exit the script and start the reset and cleanup





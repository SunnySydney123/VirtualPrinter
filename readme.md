# VirtualPrinter

A simple RAW print job listener and logger for Windows that captures print jobs sent to port 9100 (standard RAW/JetDirect protocol).

## 📋 Overview

VirtualPrinter acts as a network printer by listening on a specified IP address and port, capturing incoming print jobs, and saving them to disk for inspection or archival purposes. Each print job is saved as a `.raw` file with detailed logging in CSV format.

## ✨ Features

- **Network Print Job Capture** - Listens on port 9100 for RAW print protocol
- **IP-Based Organization** - Creates separate folders for each bound IP address
- **Detailed Logging** - CSV logs with timestamp, filename, client info, size, and duration
- **Multi-threaded** - Handles up to 50 concurrent print jobs
- **Graceful Shutdown** - Clean exit with Ctrl-C, waits for active jobs to complete
- **Interactive Setup** - Prompts for IP selection on startup with auto-detection of available interfaces

## 🔧 Requirements

- **Python 3.11+** (uses `datetime.UTC`)
- **Windows OS** (paths are Windows-specific)
- Multiple network interfaces (optional, for multi-instance deployment)

## 📦 Installation

### Option 1: Run from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/VirtualPrinter.git
cd VirtualPrinter

# Run directly
python VirtualPrinter.py
```

### Option 2: Create Standalone Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --console VirtualPrinter.py

# Find your EXE in the dist/ folder
```

## 🚀 Usage

### Basic Usage

1. Run the script:
   ```bash
   python VirtualPrinter.py
   ```

2. Select an IP address to bind to:
   ```
   Available local IP addresses:
     - 192.168.1.100
     - 192.168.2.100
     - 10.0.0.50
   
   Enter the IP to bind to (or press Enter for 0.0.0.0):
   ```

3. The listener starts and waits for incoming print jobs on port 9100

4. Print jobs are saved to: `C:\VirtualPrinter\jobs\<IP-ADDRESS>\`

### Running Multiple Instances

To capture print jobs on multiple network interfaces simultaneously:

1. Open multiple command prompts/terminals
2. Run `VirtualPrinter.py` in each window
3. Select a different IP address for each instance
4. Each instance will have its own job folder and log file

**Example Multi-Instance Setup:**
```
Instance 1: Bound to 192.168.1.100 → C:\VirtualPrinter\jobs\192.168.1.100\
Instance 2: Bound to 192.168.2.100 → C:\VirtualPrinter\jobs\192.168.2.100\
Instance 3: Bound to 10.0.0.50    → C:\VirtualPrinter\jobs\10.0.0.50\
```

## 📁 Output Structure

```
C:\VirtualPrinter\jobs\
├── 192.168.1.100\
│   ├── log.csv
│   ├── 10112025-143022-00001.raw
│   ├── 10112025-143045-00002.raw
│   └── ...
├── 192.168.2.100\
│   ├── log.csv
│   ├── 10112025-144521-00001.raw
│   └── ...
└── 10.0.0.50\
    ├── log.csv
    └── ...
```

### File Naming Convention

Print jobs are saved with the following format:
```
DDMMYYYY-HHMMSS-<sequence>.raw
```

Example: `10112025-143022-00001.raw`
- Date: November 10, 2025
- Time: 14:30:22
- Sequence: 00001

### CSV Log Format

The `log.csv` file contains:

| Column | Description |
|--------|-------------|
| `timestamp` | ISO 8601 timestamp when job completed |
| `filename` | Name of the saved `.raw` file |
| `client_ip` | IP address of the client that sent the job |
| `client_port` | Source port of the client connection |
| `bytes` | Total bytes received |
| `duration_seconds` | Time taken to receive the job |

## ⚙️ Configuration

Edit these constants in `VirtualPrinter.py` if needed:

```python
PORT = 9100              # Listening port (standard RAW/JetDirect)
BASE_OUT_DIR = r"C:\VirtualPrinter\jobs"  # Base output directory
SOCKET_TIMEOUT = 5.0     # Socket timeout in seconds
RECV_SIZE = 65536        # Receive buffer size (64KB)
MAX_WORKERS = 50         # Maximum concurrent print jobs
```

## 🔌 Client Configuration

To send print jobs to VirtualPrinter:

### Windows (Add Network Printer)
1. Control Panel → Devices and Printers → Add a printer
2. Select "The printer that I want isn't listed"
3. Choose "Add a printer using a TCP/IP address or hostname"
4. Enter the IP address where VirtualPrinter is running
5. Port: 9100
6. Install any generic PCL or PostScript driver

### Linux/Unix (CUPS)
```bash
lpadmin -p VirtualPrinter -v socket://<IP-ADDRESS>:9100 -E
```

### Command Line Testing
```bash
# Windows
type testfile.txt | nc <IP-ADDRESS> 9100

# Linux/Mac
cat testfile.txt | nc <IP-ADDRESS> 9100
```

## 🛑 Stopping the Service

- Press **Ctrl-C** in the console window
- The application will wait for active print jobs to complete before exiting
- Status messages show remaining worker threads

## 🐛 Troubleshooting

### "Cannot bind to IP:PORT"
- **Issue**: Port 9100 already in use or IP address not available
- **Solution**: Check if another instance is running, or verify the IP address exists on your system

### "No local IP addresses detected"
- **Issue**: Network interfaces not properly configured
- **Solution**: You can still bind to `0.0.0.0` (all interfaces)

### Print jobs not appearing
- **Issue**: Client not configured correctly or firewall blocking
- **Solution**: 
  - Verify firewall allows incoming connections on port 9100
  - Test with `telnet <IP-ADDRESS> 9100` from client
  - Check client printer configuration

### Empty job files
- **Issue**: Client disconnected before sending data
- **Solution**: Check network stability, increase `SOCKET_TIMEOUT` if needed

## 📝 License

Provided as-is with no warranty

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 👤 Author

**Sunil Sharma** - Tungsten Automation

## 🔮 Future Enhancements

Potential features for future versions:
- Configuration file for multi-instance deployment
- Print job format detection (PCL, PostScript, PDF)

- Automatic job cleanup/archival


## ⚠️ Disclaimer

This tool is intended for legitimate network printer testing, debugging, and archival purposes. Ensure you have proper authorization before capturing print jobs on any network.

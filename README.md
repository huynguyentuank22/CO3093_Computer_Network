# Assignment 1: P2P like-Torrent File Sharing Application
This is our implementation of the first assignment of course Computer Network (CO3093) at HCMUT, VNU.

## Team members

- Nguyen Tuan Huy
- Vo Hoang Huy
- Nguyen Van Nhat Huy

## Getting the code

You can download a copy of all the files in this repository by cloning the git repository:

    git clone https://github.com/huynguyentuank22/CO3093_Computer_Network
    cd CO3093_Computer_Network/

## Setup environment

You'll need a working Python environment to run the code.
Activate the virtual environment by running:

    source env/bin/activate // For Linux
    env\Scripts\activate // For Windows

Run pip to install dependencies.

    pip install -r requirements.txt

## Running application
Run tracker server by executing:

    python tracker.py

For each peer, you need to open a new terminal and run:

    python peer.py

You can test the application with these accounts following:

- Username: `huy`, Password: `1212!@!@`
- Username: `yuh`, Password: `12!@`
- Username: `edith`, Password: `1212!@!@`



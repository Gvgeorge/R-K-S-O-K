## Workers' and Peasants' Standard For Sending Commands (PKSOK) 1.0 

This project is a solution to the task of the course Fundamentals of Computer and Web Technologies with Python from Alexey Goloburdin.

RKSOK is a text client-server protocol, think http, but better, its advantage is that it is very safe to work with because it redirects every request to the regulatory-agency
and only prepares a request if it gets the permission. In this project only the server-side part of the protocol is implemented, client and regulatory-agent functionality were provided by the course author.

In this version of the protocol it works like a phonebook, it allows users to read, write and delete phones and other data by sending request with appropriate methods and desired names. The information is stored in separate files (one file for each name).

Main functionality is located in server.py.

Project is made with python 3.10. Required libraries can be found in requirements.txt.

To launch the project simply run python3.10 server.py in the terminal.

Conf.py is where all the configuration is located, you can change server, port, folder to save files, information about the regulatory agent, logging settings and more.

Custom exceptions are stored in exceptions.py, they are raised while parsing the request if necessary and then handled while making a response.


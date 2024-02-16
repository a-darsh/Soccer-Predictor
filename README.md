# CS-6360-Database-Project

## Setting up Environment

This project is built using python and pip, which should both be installed on the target system. You must be running python 3.9 or earlier. To install all project dependencies, run the following command from the root directory of the project:

```
pip install -r requirements.txt
```

## Executing the Application

Before you can execute the application, you must setup the environment and install the necessary tools as outlined above. To run the application, execute the following command:

```
python ./app.py
```

Once the application deploys, the url should be printed to the console. Copy and paste the url into your browser to view the frontend and use the application. 

The user interface has 2 text fields corresponding to the home and away teams for an upcoming soccer match. Due to a limited dataset, the application currently only supports the matches availble [here](https://www.betexplorer.com/football/england/premier-league/). To use the application, find a match you want predicted, enter the home and away teams (ensuring they are spelled correctly), and hit the 'Predict' button. The application will begin calculating its prediction, which will be displayed once it is completed.

Note, the application performs multiple computationally-expensive calculations, and as such can take several minutes to run. More detailed logs can be viewed on the console during execution.
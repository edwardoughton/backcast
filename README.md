# Welcome to the Backcast repository

This repository holds code for the Backasting of Mobile Infrastructure project, applied here to Mexico. 

In order to generate the results, the following scripts need to be executed:

    - Run the `preprocess.py` script in order to generate all national and regional shapes and site data. 
    - Run the `pop.py` script to extract population density estimates for a chosen regional aggregation.
    - Run the `process.py` script to generate the estimate deployment results over a specific timehorizon. 

The final results consist of a back-casted deployment schedule for the roll-out of 2G GSM, 3G UMTS and 4G LTE cellular assets, applied here to Mexico. 

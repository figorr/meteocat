# Meteocat for Home Assistant
![Meteocat Banner](images/banner.png)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python version compatibility](https://img.shields.io/pypi/pyversions/meteocat)](https://pypi.org/project/meteocat)
[![pipeline status](https://gitlab.com/figorr/meteocat/badges/master/pipeline.svg)](https://gitlab.com/figorr/meteocat/commits/master)


This is a project to obtain meteorological data from the Meteocat API inside the Home Assistant environment.

All the data is property of Meteocat ("Servei Meteorològic de Catalunya"). This project is only a tool to offer an easy and secure access to the meteorological data provided by the "Servei Meteorològic de Catalunya" API, so you can use the data for your personal use.

Commercial use of this project or the data obtained from the API is not allowed without prior permission from the author, in case of the project, or from the "Servei Meteorològic de Catalunya" in the case of the data provided by the API.

**NOTE:** Meteocat API requires to use an API_KEY, you should ask to (https://apidocs.meteocat.gencat.cat/documentacio/acces-ciutada-i-administracio/)

# Credits

This is a personal project.

Authors:
- Figorr

## Installation

#### HACS - Install using the custom repository method.

1. First of all you need to add a custom repository like [this](https://hacs.xyz/docs/faq/custom_repositories/).
1. Then download the integration from HACS.
1. Restart Home Assistant.
1. Go to `Settings > Devices & Services`
1. Click `+ Add Integration`
1. Search for `Meteocat` and follow the configuration instructions


#### HACS - Install from the store
1. Go to `HACS`
1. Search for `Meteocat` and add it to HACS
1. Restart Home Assistant
1. Go to `Settings > Devices & Services`
1. Click `+ Add Integration`
1. Search for `Meteocat` and follow the configuration instructions

#### Manually
Copy the `custom_components/meteocat` folder into the config folder.

## Configuration
To add a Meteocat Device, go to `Configuration > Integrations` in the UI. Then click the `+` button and from the list of integrations select Meteocat. You will then be prompted to enter your API Key.

![Meteocat custom component login dialog](images/login.png)

After submitting your API Key you will either be prompted to pick a town from the list as shown below.

![Meteocat custom component town picker dialog](images/pick_town.png)

Once you pick the town you will be prompted to pick a station from the list. These are the nearest stations to the picked town.

![Meteocat component station picker dialog](images/pick_station.png)

Then you will be asked to pick an area for the device.

![Area](images/pick_area.png)

If the device is added successfully it should appear as shown.

![Device](images/devices.png)

This device will then have the entities shown below. The sensors are translated to your system language (according to tranlation folder: en, es, ca). Or English by default.

![Dynamic Sensors](images/dynamic_sensors.png)

![Diagnostic Sensors](images/diagnostic_sensors.png)

## Changing Units

To change units select one of the entities and open the more info dialog and click the cog in the top right. This will bring up the settings for the entity. Then select `Unit of Measurement`, and a dropdown will appear where you can select the units you want.

![Entity more info settings dialog](images/change_units.png)

# Contributing

1.  [Check for open features/bugs](https://gitlab.com/figorr/meteocat/issues)
    or [initiate a discussion on one](https://gitlab.com/figorr/meteocat/issues/new).
2.  [Fork the repository](https://gitlab.com/figorr/meteocat/forks/new).
3.  Install the dev environment: `make init`.
4.  Enter the virtual environment: `pipenv shell`
5.  Code your new feature or bug fix.
6.  Write a test that covers your new functionality.
7.  Update `README.md` with any new documentation.
8.  Run tests and ensure 100% code coverage for your contribution: `make coverage`
9.  Ensure you have no linting errors: `make lint`
10. Ensure you have typed your code correctly: `make typing`
11. Add yourself to `AUTHORS.md`.
12. Submit a pull request!

# License

[Apache-2.0](LICENSE). By providing a contribution, you agree the contribution is licensed under Apache-2.0.

# API Reference

[See the docs 📚](https://apidocs.meteocat.gencat.cat/section/informacio-general/).
"""Python Package: Meteocat package to access weather data through the Meteocat API.

SPDX-License-Identifier: Apache-2.0

For more details about this api, please refer to the documentation at
https://gitlab.com/figorr1/meteocat
"""

import logging

# Version
__version__ = "0.1.6"

# Configuración básica para el sistema de logging
logging.basicConfig(
    level=logging.INFO,  # Cambia a logging.DEBUG durante el desarrollo
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

_LOGGER = logging.getLogger(__name__)

_LOGGER.info("Paquete meteocat inicializado")
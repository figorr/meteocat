# [4.0.0](https://github.com/figorr/meteocat/compare/v3.2.0...v4.0.0) (2025-11-07)


## 🚀 Release Meteocat integration v4.0.0 — major improvements and new solar/lunar system
My own custom Python package `Solarmoonpy` is introduced in this major release.
`Solarmoonpy` added support for new native sun and moon sensors in the Meteocat integration.

### ✨ Highlights:
- Introduced new Python package `Solarmoonpy` to handle all solar and lunar data and event calculations.
  → Replaces the `astral` dependency completely.
- Added new solar and lunar sensors to provide richer astronomical data with many extra attributes.
- Added configuration option to manually adjust default coordinates and elevation.
  → This allows users to fine-tune their position for more accurate solar and lunar event calculations instead of using the default station coordinates and elevation.

### 🛠 Changes:
- Major refactor and optimization of coordinator logic for better performance and stability.
- The default validation hour for forecasts is set to 6.

### ⚠️ Note:
- The new v4.0.0 is required for using Meteocat Card v3.0.0 and later.
- Upgrade is recommended if you plan to use the updated card.

# [3.2.0](https://github.com/figorr/meteocat/compare/v3.1.0...v3.2.0) (2025-11-07)


### Bug Fixes

* add validation date for moon coordinator ([8644f56](https://github.com/figorr/meteocat/commit/8644f56d8f8b6b607ba8809499afbfb81eb70b28))
* adjust moon update interval ([ea51d90](https://github.com/figorr/meteocat/commit/ea51d905a232ab947607333ea4abaf449cd2e786))
* fix friendly time translation ([9081a34](https://github.com/figorr/meteocat/commit/9081a343fd1562cb001f8a4b69948be3e26cbe00))
* fix reset data moon file coordinator ([f3cf22f](https://github.com/figorr/meteocat/commit/f3cf22f1fb1d1a19d6ee9fefd2be304850be1180))
* more accurate moon calculation ([dcee6e0](https://github.com/figorr/meteocat/commit/dcee6e0040d1cf77860fc7cbd06a5518145d3a72))


### Features

* add new moon day data ([77edf68](https://github.com/figorr/meteocat/commit/77edf681af037f00748b2b3cf2d281655d225718))
* add new moon day data ([d2be96e](https://github.com/figorr/meteocat/commit/d2be96ec7f4f9d48c1f018ba2c642f29558d05fe))
* add translations for lunation attribute ([10e3409](https://github.com/figorr/meteocat/commit/10e3409f82fa6530f0edf81c5e8406d019aeeaf1))
* bump solarmoonpy to v1.0.0 ([65c2a04](https://github.com/figorr/meteocat/commit/65c2a0495250bac284c060b575256f95f4fb0be0))
* bump solarmoonpy to v1.0.1 ([aa86747](https://github.com/figorr/meteocat/commit/aa86747ed41d69a80ac009b75b596746762548fe))
* bump solarmoonpy to v1.0.3 ([246bd83](https://github.com/figorr/meteocat/commit/246bd835589978940efc11722b79e420f838ecab))
* include latitude, longitude and altitude as new required variables ([5ef864c](https://github.com/figorr/meteocat/commit/5ef864ca38fa17ed05b36a19a96b8c7182f66be7))
* new latitude, longitude and altitude update options setup ([1aeb968](https://github.com/figorr/meteocat/commit/1aeb9682c8e65b3cb0b29a7b7467edcc455304c9))
* new lunation attribute for moon and moon phase name code ([60c7129](https://github.com/figorr/meteocat/commit/60c7129757916908baf26439819458ea3a173ad4))
* new lunation attribute for moon sensor ([9bb32ff](https://github.com/figorr/meteocat/commit/9bb32ff03bd7eba291a1ee1aa578e2838dcf9bd5))
* new lunation data and moon phase name rework ([0616401](https://github.com/figorr/meteocat/commit/0616401243334c21736d0877e5e50e435279e002))
* new moon day attribute ([86ec6e3](https://github.com/figorr/meteocat/commit/86ec6e311fc098174027f17d3502e8be740d7e86))
* new moon sensors ([7c7c1d3](https://github.com/figorr/meteocat/commit/7c7c1d38393a40fd2e69eeba2c24bb185ae349ef))
* new solarmoonpy requirement for sun and moon events calculation ([1d25a62](https://github.com/figorr/meteocat/commit/1d25a6252cf568e1242f654c389aeada2b5d73f6))
* new sun and moon coordinators ([af2290e](https://github.com/figorr/meteocat/commit/af2290e7384a9ad5416afdf4d6767ad69099813c))
* new sun and moon files ([b489d7a](https://github.com/figorr/meteocat/commit/b489d7a9abc5af747fc50a2e0d7b0d661408b824))
* new sun and moon sensors ([91265f3](https://github.com/figorr/meteocat/commit/91265f3c6cbd512b3706c29d466f9bb01df6d45e))
* translation for new moon day attribute ([162859e](https://github.com/figorr/meteocat/commit/162859e2822374b81835cb1af07325dceaf5a55e))
* translations for the new moon and sun sensors ([91a33b6](https://github.com/figorr/meteocat/commit/91a33b6b52e34ed69eed4eb5fbfaf9dffd20df57))

# [3.1.0](https://github.com/figorr/meteocat/compare/v3.0.0...v3.1.0) (2025-09-27)


### Bug Fixes

* fix unknown threshold translation ([6fa7964](https://github.com/figorr/meteocat/commit/6fa79644e3ebbdf9a44826f6071af6009cd2d02d))
* include Meteocat Card ([513d9ed](https://github.com/figorr/meteocat/commit/513d9ed50fcd9127ac64f0388ed1017db938f378))


### Features

* ✨ Add native sunrise and sunset sensors to Meteocat integration ([7bb70c6](https://github.com/figorr/meteocat/commit/7bb70c681c90773275e496f938f455c3688fb4c0))

## [3.0.0](https://github.com/figorr/meteocat/compare/v2.3.0...v3.0.0) (2025-09-14)


### ⚠️ BREAKING CHANGES

* Version **3.0.0 and later** introduces a **breaking change** in how entities are identified.

## ⚠️ What this affects
- This affects any update **from a version prior to 3.0.0** to **any version 3.x or later**. 
- Entities now use **`town_id`** instead of `region_id` in their `unique_id`.  
- This change allows multiple integration entries that share the same `region_id` but different towns.  

### ✅ Recommended upgrade procedure
To avoid issues with duplicated or unavailable entities:

1. **Uninstall** the existing integration (v2.x).  
2. **Restart** Home Assistant.  
3. **Install v3.0.0 or later** and configure the integration again.  

### 🚨 If you update directly
If you update without uninstalling first:

- Old entities will remain as **Unavailable**.  
- New entities will be created (sometimes with a suffix like `2`).  
- You may need to manually **remove old entities** and update your automations, dashboards, or scripts to point to the new entities.

### 📑 Additional notes

- This change affects all entity types, including **sensors, diagnostic sensors, and alerts**.  
- Always backup your **Home Assistant configuration** before performing major upgrades.

ℹ️ More details:  
- [README – Breaking changes](https://github.com/figorr/meteocat#-breaking-changes---upgrade-to-3x)  
- [Wiki – Breaking changes](https://github.com/figorr/meteocat/wiki/Breaking-Changes)

### Features

* change unique_id to use town_id ([3a048ce](https://github.com/figorr/meteocat/commit/3a048ce48a0e1f3ee7642c28bbe7ac6e6e3fc298))

### Contributors:  
- [mcasellas](https://github.com/mcasellas) – contributed [c505f27](https://github.com/figorr/meteocat/commit/c505f27) - Improve Catalan translations


## [2.3.0](https://github.com/figorr/meteocat/compare/v2.2.7...v2.3.0) (2025-09-10)


### Features

* download and save town and station json files during setup ([7b98c22](https://github.com/figorr/meteocat/commit/7b98c22d5ca43d4cbf80895e11c02594208f7470))
* include options documentation ([a85ef74](https://github.com/figorr/meteocat/commit/a85ef7492eb8ed4af99b8d0f50b8e77ff7f7976a))
* include options image ([dbb047a](https://github.com/figorr/meteocat/commit/dbb047a6bdf32af03fec8351c9a608593b369e3b))
* include regenerate assets files option ([f2ce357](https://github.com/figorr/meteocat/commit/f2ce357c8ce6371d97523870f4bf6a9cba6a151c))
* recover assets files ([f493b33](https://github.com/figorr/meteocat/commit/f493b33e54e10994b6b08232f37dd5bb35f4a9b7))
* regenerate assets option translation ([317ce9f](https://github.com/figorr/meteocat/commit/317ce9fecc03f88b8b8072b41b357846fb075dcc))
* safe remove keeping common entry files ([6cefe04](https://github.com/figorr/meteocat/commit/6cefe04289b1b74fe30d615e7056bd643d845b89))
* **storage:** moving the API downloaded files to the new folder meteocat_files ([06c68e3](https://github.com/figorr/meteocat/commit/06c68e36b5669efc8fe3174a71e41624e9728b07))
* update .gitignore ([fac7772](https://github.com/figorr/meteocat/commit/fac7772a1093f2165e1b33098631096138617a6d))
* update README ([9855939](https://github.com/figorr/meteocat/commit/98559398e6bae30e8e9c9ff2b2fe27409a3930bd))
* update repo files structure ([0778679](https://github.com/figorr/meteocat/commit/0778679d218a89e89bb18791f1245c5c9f7b188f))


## [2.2.7](https://github.com/figorr/meteocat/compare/v2.2.6...v2.2.7) (2025-08-29)


### Bug Fixes

* 2.2.7 ([ece96b9](https://github.com/figorr/meteocat/commit/ece96b983e6ba5df8a2811fdb86452857cadbb18))
* fix HACS info ([ae829fa](https://github.com/figorr/meteocat/commit/ae829fa09047bd57d8f5aa8eae746bf31f3a30db))
* Fix meteor case sensitive for alerts sensors ([d247476](https://github.com/figorr/meteocat/commit/d24747660175d2c305fcffbbae6472ccd490cfb1))
* Fix umbral case insensitive ([73d6b58](https://github.com/figorr/meteocat/commit/73d6b5808acf8c896a7d822cab7640607f430b37))
* Fix warning log when an umbral is not in UMBRAL_MAPPING ([adf3511](https://github.com/figorr/meteocat/commit/adf351111e8cb14cba3fd2f2868496701b445b97))
* Include warning when umbral is not at UMBRAL_MAPPING ([c1b1f75](https://github.com/figorr/meteocat/commit/c1b1f75d7b6a219fbce4580a29e85e168127998e))

## [2.2.6](https://github.com/figorr/meteocat/compare/v2.2.5...v2.2.6) (2025-08-27)


### Bug Fixes

* 2.2.6 ([bb92000](https://github.com/figorr/meteocat/commit/bb9200099ed951168bc891c870c6fd61b758c73d))
* Fix alerts region data update at first setup of the next entrances ([40018dc](https://github.com/figorr/meteocat/commit/40018dc0bb703a8dc606aaedcfa27b5c3e6bbf7a))
* Fix delete an entry but keeping common files for the rest of entries ([211e545](https://github.com/figorr/meteocat/commit/211e54510c458378ca46c465303995d1a9df0dbb))
* Fix region alerts json file for multiple entrances ([2b7072c](https://github.com/figorr/meteocat/commit/2b7072cb6fd7eafa1ab95dcedb2c2dea8f35005d))

## [2.2.5](https://github.com/figorr/meteocat/compare/v2.2.4...v2.2.5) (2025-02-16)


### Bug Fixes

* 2.2.5 ([cd8fb52](https://github.com/figorr/meteocat/commit/cd8fb52c607e3a74308246136b6ac2d47b51e125))
* fix lightning status sensor native value ([dc3badc](https://github.com/figorr/meteocat/commit/dc3badc7b66d9afbcc14e23da3f0909f845cef2f))
* fix validity at lightning coordinator and cached data ([d959bc5](https://github.com/figorr/meteocat/commit/d959bc56dfb19a475b2e34a2649bbabd803ab41e))
* new lighting validity hour ([eab0215](https://github.com/figorr/meteocat/commit/eab0215cc3d68de9f900a4ecf1844ef3c6c22610))

## [2.2.4](https://github.com/figorr/meteocat/compare/v2.2.3...v2.2.4) (2025-02-09)


### Bug Fixes

* 2.2.4 ([59183ea](https://github.com/figorr/meteocat/commit/59183ea082f6d963e46d3f8a51e0867b3f32060d))
* fix valid lightning data for download from API ([4e4a8ae](https://github.com/figorr/meteocat/commit/4e4a8ae110b72b6e6ff560921f88ea7fb4640a29))

## [2.2.3](https://github.com/figorr/meteocat/compare/v2.2.2...v2.2.3) (2025-02-08)


### Bug Fixes

* 2.2.3 ([ce224a0](https://github.com/figorr/meteocat/commit/ce224a097e7c879c46985ff3a16143de1b822006))
* bump meteocatpy to 1.0.1 ([7119065](https://github.com/figorr/meteocat/commit/711906534fca5c61a9a3ab968a3572e70f05929e))
* new lightning sensors ([8528f57](https://github.com/figorr/meteocat/commit/8528f57d688f7fc21f66715ffeac086895afd1aa))
* update README ([10c86e5](https://github.com/figorr/meteocat/commit/10c86e5e373c661cf23524421c756374711d89fe))

## [2.2.2](https://github.com/figorr/meteocat/compare/v2.2.1...v2.2.2) (2025-02-04)


### Bug Fixes

* 2.2.2 ([3667e5d](https://github.com/figorr/meteocat/commit/3667e5d65069ee0079ebbaebeab6c929be8b9630))
* fix version 2.2.1 ([359cc7f](https://github.com/figorr/meteocat/commit/359cc7f7a9f1f025890bedc5177785016e9968d1))

# [2.1.0](https://github.com/figorr/meteocat/compare/v2.0.3...v2.1.0) (2025-01-27)


### Bug Fixes

* 2.1.0 ([759c293](https://github.com/figorr/meteocat/commit/759c2932fea8e4f174a753eca5b4c09f9d2549b6))


### Features

* fix version ([596ee59](https://github.com/figorr/meteocat/commit/596ee59a835ee913238f66d40869ce27a53da4e9))

## [2.0.3](https://github.com/figorr/meteocat/compare/v2.0.2...v2.0.3) (2025-01-27)

* 2.0.3

### Bug Fixes


## [2.0.2](https://github.com/figorr/meteocat/compare/v2.0.1...v2.0.2) (2025-01-27)

* 2.0.2

### Bug Fixes

* 2.0.1 ([7e95865](https://github.com/figorr/meteocat/commit/7e958659305f7f3a3049a8bcee1c713f60ff56ca))

## [2.0.0](https://github.com/figorr/meteocat/compare/v1.1.1...v2.0.0) (2025-01-26)


### Bug Fixes

* 2.0.0 ([8f9ad16](https://github.com/figorr/meteocat/commit/8f9ad169b92da1093c3cdb2ff64ad5ffae9c9b24))
* update installation methods at README ([e588ffa](https://github.com/figorr/meteocat/commit/e588ffa17c10652992a4c26d19d26b7757b051b5))
* new alert sensors feature

## [1.1.1](https://github.com/figorr/meteocat/compare/v1.1.0...v1.1.1) (2025-01-08)


### Bug Fixes

* 1.1.1 ([0dc7429](https://github.com/figorr/meteocat/commit/0dc74293881bfb50b9a6a62cc174254451a320cc))
* bump meteocatpy to 0.0.20 ([91b03c8](https://github.com/figorr/meteocat/commit/91b03c80e448d4cde03aef2dab87041a511de02a))

# [1.1.0](https://github.com/figorr/meteocat/compare/v1.0.2...v1.1.0) (2025-01-05)


### Bug Fixes

* 1.1.0 ([b0e0d9a](https://github.com/figorr/meteocat/commit/b0e0d9a3aa3d2f13bb4eff129311c8c6d4e04304))


### Features

* add wind bearing to weather entity ([0d40460](https://github.com/figorr/meteocat/commit/0d40460947466a644a51da3bf3361e89383ccbfe))
* new wind direction cardinal sensor ([c430c48](https://github.com/figorr/meteocat/commit/c430c48a0621dbd1270a040ef017aff2c6dadc28))

## [1.0.2](https://github.com/figorr/meteocat/compare/v1.0.1...v1.0.2) (2025-01-05)


### Bug Fixes

* 1.0.2 ([8ec865b](https://github.com/figorr/meteocat/commit/8ec865b4d09e802bd489bc527dbfa74de5084cb7))
* include CONFIG_SCHEMA ([8911de2](https://github.com/figorr/meteocat/commit/8911de29c1804c63b79780f0bb057fdf3681eaec))

## [1.0.1](https://github.com/figorr/meteocat/compare/v1.0.0...v1.0.1) (2025-01-04)


### Bug Fixes

* 1.0.1 ([c2f56d7](https://github.com/figorr/meteocat/commit/c2f56d7243649cf48ce1a1d84761c05762832e8c))
* fix directions translation key ([3545d7c](https://github.com/figorr/meteocat/commit/3545d7cee8662462de4a3ed3c164d9d4a7e5e854))
* fix hacs.json file removing iot_class ([03d3db0](https://github.com/figorr/meteocat/commit/03d3db08beb94a5d7c92aa0960a6ff627256e88a))
* fix order in manifest.json ([434e3d5](https://github.com/figorr/meteocat/commit/434e3d50a5369a5a7c9deda0130a691d5e71b991))
* fix wind direction translation keys ([3a73291](https://github.com/figorr/meteocat/commit/3a73291d803b72890d627eeb5814be17d22ab6b4))

## [1.0.0](https://github.com/figorr/meteocat/compare/v0.1.51...v1.0.0) (2025-01-04)


### Bug Fixes

* 1.0.0 ([a1ec6cf](https://github.com/figorr/meteocat/commit/a1ec6cf411dcb208eeb153b00b73bf9f766d7f23))

## [0.1.51](https://github.com/figorr/meteocat/compare/v0.1.50...v0.1.51) (2025-01-04)


### Bug Fixes

* 1.0.0 ([a1ec6cf](https://github.com/figorr/meteocat/commit/a1ec6cf411dcb208eeb153b00b73bf9f766d7f23))

## [0.1.50](https://github.com/figorr/meteocat/compare/v0.1.49...v0.1.50) (2025-01-04)


### Bug Fixes

* 0.1.50 ([cbfc022](https://github.com/figorr/meteocat/commit/cbfc0228195762f7af306a85db4c03b287cd3c24))
* fix precipitation unit ([9e6d5aa](https://github.com/figorr/meteocat/commit/9e6d5aa85ce3450341d70e2edff9a13880c69a89))

## [0.1.49](https://github.com/figorr/meteocat/compare/v0.1.48...v0.1.49) (2025-01-03)


### Bug Fixes

* 0.1.49 ([81dea76](https://github.com/figorr/meteocat/commit/81dea7618fc1b3fd6aa4edff923720e424ca7f8d))
* add daily precipitation probability sensor ([4d59c3f](https://github.com/figorr/meteocat/commit/4d59c3f9480c09da678fd6ce7efa775619a17d86))
* add daily precipitation probability sensor ([c786f26](https://github.com/figorr/meteocat/commit/c786f26d36b8f17bb9512d405a5a2ba921a8b881))

## [0.1.48](https://github.com/figorr/meteocat/compare/v0.1.47...v0.1.48) (2025-01-03)


### Bug Fixes

* 0.1.48 ([b8b8830](https://github.com/figorr/meteocat/commit/b8b8830a23b0d63744f30c3dff33fc9f172a3c01))
* fix UTC to local time conversion ([14cf7d2](https://github.com/figorr/meteocat/commit/14cf7d2ca696ede2bedcd6041195df44fdd6d245))

## [0.1.47](https://github.com/figorr/meteocat/compare/v0.1.46...v0.1.47) (2025-01-02)


### Bug Fixes

* 0.1.47 ([03d1d08](https://github.com/figorr/meteocat/commit/03d1d08dd837dc47d8f2062ba561be706e1d8b05))
* convert to local time from UTC ([0dfe9f9](https://github.com/figorr/meteocat/commit/0dfe9f9ef7409bcd23d839963076aff14921f114))
* fix semantic-release-bot ([754f18b](https://github.com/figorr/meteocat/commit/754f18b2c0378c704eb255259192655b76100c43))
* fix timestamp sensor from UTC to local time Europe/Madrid ([e64539a](https://github.com/figorr/meteocat/commit/e64539a091adecfd4e23419c63bc54eda2293da3))

## [0.1.46](https://github.com/figorr/meteocat/compare/v0.1.45...v0.1.46) (2025-01-01)


### Bug Fixes

* 0.1.46 ([e2e736e](https://github.com/figorr/meteocat/commit/e2e736e102f25da704060bc6329696eec8c8fac6))
* add validity days, hours and minutes ([61a6761](https://github.com/figorr/meteocat/commit/61a6761cde31c321dbed4dce126416f65062a90f))

## [0.1.45](https://github.com/figorr/meteocat/compare/v0.1.44...v0.1.45) (2024-12-31)


### Bug Fixes

* 0.1.45 ([ab522cf](https://github.com/figorr/meteocat/commit/ab522cf4d94687c64dc84480f8f5507645a79557))
* change icon for status sensors ([7415646](https://github.com/figorr/meteocat/commit/741564698b09b6e29b774bb388b6c96f718a573a))
* fix async_add_entities for generic dynamic sensors ([2192214](https://github.com/figorr/meteocat/commit/2192214ebb767e74c187df98e7c811225c21ca33))
* fix name and comments for Temp Forecast Coordinator ([e65e476](https://github.com/figorr/meteocat/commit/e65e476f03b0de062ab14a9563eaa71b6d80301f))
* fix name sensor coordinator ([e93d01f](https://github.com/figorr/meteocat/commit/e93d01f359158ee63494e697059550fcea37806f))

## [0.1.44](https://github.com/figorr/meteocat/compare/v0.1.43...v0.1.44) (2024-12-30)


### Bug Fixes

* 0.1.44 ([7a506ea](https://github.com/figorr/meteocat/commit/7a506eab7e1fa1c0975561d71520ec3e146019dd))
* add date attribute for status sensors ([5663be5](https://github.com/figorr/meteocat/commit/5663be50ba007debe349aa730a7e735f8d448a8b))
* add state translations for file status ([32bcd61](https://github.com/figorr/meteocat/commit/32bcd611cddf773046ee07043a8578a6cbc52f94))
* add translations for status sensors date attribute ([9504a58](https://github.com/figorr/meteocat/commit/9504a5809fbc83ed2bba0b507354260d6606b7c5))

## [0.1.43](https://github.com/figorr/meteocat/compare/v0.1.42...v0.1.43) (2024-12-30)


### Bug Fixes

* 0.1.43 ([13185b2](https://github.com/figorr/meteocat/commit/13185b2276a5efb02b4fd18d07d30ab03ca7357d))
* add info station to config_flow ([6c8c652](https://github.com/figorr/meteocat/commit/6c8c652dc54788e2b471984726dc7dd3c0ba30d6))
* add new hourly, daily and uvi file status sensors ([42aa8b2](https://github.com/figorr/meteocat/commit/42aa8b2abbf6b333287c15d92e19b69d9630e62e))
* add new hourly, daily and uvi file status sensors translations ([5639489](https://github.com/figorr/meteocat/commit/563948999feb077a5effe9c07df9dda950469d73))
* add new hourly, daily and uvi sensor constants ([f7a4814](https://github.com/figorr/meteocat/commit/f7a481435abf34926b52312cc5302045c9357e69))
* fix entity and uvi coordinator ([ee3a557](https://github.com/figorr/meteocat/commit/ee3a5571e5e08737b3393a650509732b1cd4996a))
* ignore test read json date ([f5ce2ed](https://github.com/figorr/meteocat/commit/f5ce2edfa77d1ec33c4beff8c5c775499c0564fe))
* include entity and uvi coordinators ([4128d39](https://github.com/figorr/meteocat/commit/4128d3902bd67414eaee6d8d6da4628ecbce3493))
* set region, province and status to str ([31f58e7](https://github.com/figorr/meteocat/commit/31f58e7d701b2499e4f4d9f385238368703c75ff))

## [0.1.42](https://github.com/figorr/meteocat/compare/v0.1.41...v0.1.42) (2024-12-28)


### Bug Fixes

* 0.1.42 ([f180cf1](https://github.com/figorr/meteocat/commit/f180cf1400e614684cfee81849369bb74796ee5e))
* bump meteocatpy to 0.0.16 ([0e14f79](https://github.com/figorr/meteocat/commit/0e14f79445ee4c059d47a315bcbdc20858a0c666))
* set logger to warning when using cache data ([b840d72](https://github.com/figorr/meteocat/commit/b840d7202c439f83b08597b9365c007e92aca1c5))

## [0.1.41](https://github.com/figorr/meteocat/compare/v0.1.40...v0.1.41) (2024-12-27)


### Bug Fixes

* 0.1.41 ([ba2c800](https://github.com/figorr/meteocat/commit/ba2c80048cc2da6efe5f950a5d8fb958a53a7ef6))
* add new Max and Min Today Temperature sensors ([6cc726d](https://github.com/figorr/meteocat/commit/6cc726d127432ddc13a54638157f1f9566967ed4))
* add Today temp max and min translations ([8e1d31e](https://github.com/figorr/meteocat/commit/8e1d31e78c1d5df61c37635a19d95b6339f0b0a5))
* add Today temp max and min translations ([041c3ab](https://github.com/figorr/meteocat/commit/041c3ab877b269f3b3d3359792ecf13b14969466))
* add Today temp max and min translations ([be25fc4](https://github.com/figorr/meteocat/commit/be25fc43bef58e1cecc2afaff8e0b8d3288399fb))
* add Today temp max and min translations ([e236182](https://github.com/figorr/meteocat/commit/e236182dfe29b15c3eb06d6a8fd3e02712837858))
* fix condition when is night ([fb64e0b](https://github.com/figorr/meteocat/commit/fb64e0b754eb5a39afe9135a0be842d5e8bdeae0))
* fix sunset and sunrise events for night flag ([4770e56](https://github.com/figorr/meteocat/commit/4770e5633707933c0bdd2aae0f74ada363da86bb))

## [0.1.40](https://github.com/figorr/meteocat/compare/v0.1.39...v0.1.40) (2024-12-26)


### Bug Fixes

* 0.1.40 ([011f139](https://github.com/figorr/meteocat/commit/011f1391874a78d16c1ad1eebbd8f84e6b053b5b))
* fix hourly forecasts ([bc1aa17](https://github.com/figorr/meteocat/commit/bc1aa178222a7158590b32af442427def4187e38))

## [0.1.39](https://github.com/figorr/meteocat/compare/v0.1.38...v0.1.39) (2024-12-25)


### Bug Fixes

* 0.1.39 ([be7e9f3](https://github.com/figorr/meteocat/commit/be7e9f394a02be59521fce9a20100d3091092358))
* add conditions constants ([95fa3bb](https://github.com/figorr/meteocat/commit/95fa3bba33722d2d976e1545bb58a7f97636ab7b))
* add MeteocatEntityCoordinator and def json to save files ([f5816cc](https://github.com/figorr/meteocat/commit/f5816cc71dd2d7f4900c796d482969742a67ca05))
* add MeteocatyEntityCoordinator and update async_remove_entry ([99a9883](https://github.com/figorr/meteocat/commit/99a98837de9923ba4a8604b5ff5ea6e628a51097))
* add translations to new condition sensor ([92d757c](https://github.com/figorr/meteocat/commit/92d757c82bf9c33bd392d16f74d666f806fc27cb))
* add weather entity ([914c407](https://github.com/figorr/meteocat/commit/914c4076457c8dd2ff1527ef83e5f62b911112a1))
* fix condition code ([04c6ea3](https://github.com/figorr/meteocat/commit/04c6ea3e668b19bad95141154ffa6910d4aa8f3a))
* fix is night code ([d50d587](https://github.com/figorr/meteocat/commit/d50d5871d89eb3ae20217e2070db61dcfc6c2503))
* fix uvi icon ([d16d452](https://github.com/figorr/meteocat/commit/d16d45282f5eae83f5a337a58d34d5c5e62bee6f))
* new condition sensor ([8f352fc](https://github.com/figorr/meteocat/commit/8f352fcff6f97e1bfe9ea49d22f03837b177f680))
* new repo file structure ([ac61261](https://github.com/figorr/meteocat/commit/ac612613e386f926eed526e2796cadd325a3fabc))
* new weather and condition coordinators ([f8307d8](https://github.com/figorr/meteocat/commit/f8307d8d8de915592c3a285e91dc8c79164953b5))
* new weather and condition coordinators ([4c457e8](https://github.com/figorr/meteocat/commit/4c457e87f17564fa50743064dfbdd922e4babc17))
* use await to save json files ([0945320](https://github.com/figorr/meteocat/commit/09453205bf891dcfef811c2628e72bf921aac8bb))

## [0.1.38](https://github.com/figorr/meteocat/compare/v0.1.37...v0.1.38) (2024-12-18)


### Bug Fixes

* 0.1.38 ([58014ef](https://github.com/figorr/meteocat/commit/58014ef56ca54f2b458fe6e142fbcf27cd8d211d))
* add degrees attribute translations ([341cf84](https://github.com/figorr/meteocat/commit/341cf849024f98ff1f31b66ec7ff6a2a39123148))
* add degrees property to wind direction ([9570a79](https://github.com/figorr/meteocat/commit/9570a7911d112624818da224369bacec1ee74902))

## [0.1.37](https://github.com/figorr/meteocat/compare/v0.1.36...v0.1.37) (2024-12-17)


### Bug Fixes

* 0.1.37 ([1e850d8](https://github.com/figorr/meteocat/commit/1e850d8e77d0e572a0bfb8ba01702ab3acf0437f))
* fix hour attribute translation ([31ccc6f](https://github.com/figorr/meteocat/commit/31ccc6fc9a1a51c441935682cbdc1af07cc6af5f))
* fix wind directions ([23bbf44](https://github.com/figorr/meteocat/commit/23bbf4465c79107e5326fc107b23cf4a0c71c70c))

## [0.1.36](https://github.com/figorr/meteocat/compare/v0.1.35...v0.1.36) (2024-12-17)


### Bug Fixes

* 0.1.36 ([73da4ed](https://github.com/figorr/meteocat/commit/73da4ed7c598a150528294e89c93407e33abfd24))
* add hour attribute to UVI sensor ([a365626](https://github.com/figorr/meteocat/commit/a365626aa2bb585ca9a835afcec6cea99e85a4bd))
* add hour attribute translation ([d50f8bb](https://github.com/figorr/meteocat/commit/d50f8bbbcb3c8867dedcbe51f065951f5dfab817))
* fix self. _config.entry from deprecated self. config.entry ([ed4bfeb](https://github.com/figorr/meteocat/commit/ed4bfebf0ea45bc63de000a21f6063a0cb9e499a))
* ignore uvi test ([cf35867](https://github.com/figorr/meteocat/commit/cf358675b1afce3e1ea1650414a22c2372af4b49))
* set coordinators to uvi sensor ([38288cc](https://github.com/figorr/meteocat/commit/38288cc75a30a1ad77a492dcb2b15592379e774f))
* set uvi coordinators ([1ea0432](https://github.com/figorr/meteocat/commit/1ea0432d6749cac96d45e52d3cf18e7a83e59739))
* update devs ([9274984](https://github.com/figorr/meteocat/commit/9274984154facd81bdeaf0e0050c870a08996b10))
* update devs ([44d7699](https://github.com/figorr/meteocat/commit/44d7699c4d3bde13f6145a5380eafc5c77818c45))
* use cached data when API failed ([f31bd10](https://github.com/figorr/meteocat/commit/f31bd10539e77f7d3e12bc27b3bf88cc9ab317d2))
* uvi sensor ([ee0b194](https://github.com/figorr/meteocat/commit/ee0b19461bdfacc26d493f9af0e27729e45ae545))

## [0.1.35](https://github.com/figorr/meteocat/compare/v0.1.34...v0.1.35) (2024-12-14)


### Bug Fixes

* 0.1.35 ([87adbc5](https://github.com/figorr/meteocat/commit/87adbc5c76941af1ff837f63920ca65164df38c2))
* fix station data json name ([2c411bd](https://github.com/figorr/meteocat/commit/2c411bd5d040d8c50bd00dae3c4b7858c049e522))

## [0.1.34](https://github.com/figorr/meteocat/compare/v0.1.33...v0.1.34) (2024-12-14)


### Bug Fixes

* 0.1.34 ([14c1437](https://github.com/figorr/meteocat/commit/14c1437a95fd41a014146fd63ce80892a2d4a284))
* fix data validation ([a2c4282](https://github.com/figorr/meteocat/commit/a2c428207b062a06c5c07377ab3bf8ffbc65d277))
* fix Feels Like round(1) ([6329807](https://github.com/figorr/meteocat/commit/63298077e5aa09cb61413b0578ccd7e4baeb5c51))
* remove data validation ([250e582](https://github.com/figorr/meteocat/commit/250e5825dbda556e3e8e0c2e4a8014993e1de705))
* set timeout and data validation ([b7dba2e](https://github.com/figorr/meteocat/commit/b7dba2e9e742bee04c8e16d3694c7ac647ec83ab))

## [0.1.33](https://github.com/figorr/meteocat/compare/v0.1.32...v0.1.33) (2024-12-14)


### Bug Fixes

* 0.1.33 ([461a423](https://github.com/figorr/meteocat/commit/461a423bd8596234bc182697d9f2725dd5234334))
* fix feels like options ([8e22c9e](https://github.com/figorr/meteocat/commit/8e22c9efd175d84eede50b4ce5c1f7abac14dc00))

## [0.1.32](https://github.com/figorr/meteocat/compare/v0.1.31...v0.1.32) (2024-12-14)


### Bug Fixes

* 0.1.32 ([7c6186f](https://github.com/figorr/meteocat/commit/7c6186fe81061013f6093355b042750fbc28b921))
* add LOGGER debug to FEELS LIKE ([a0cd0c4](https://github.com/figorr/meteocat/commit/a0cd0c495b1f01365a74d6262ed595921962b825))
* add translations names to sensors ([57a5a1c](https://github.com/figorr/meteocat/commit/57a5a1c734db1042b1085c8fb58140c1dc0ad1fb))
* add wind direction translations ([f4ec133](https://github.com/figorr/meteocat/commit/f4ec1339126d4da008e0cbc2a96fff8be3c6e081))

## [0.1.31](https://github.com/figorr/meteocat/compare/v0.1.30...v0.1.31) (2024-12-13)


### Bug Fixes

* 0.1.31 ([6d49197](https://github.com/figorr/meteocat/commit/6d4919717b09d4e38a3225bf9a33d1400a0227d0))
* add feels like sensor ([caca7a0](https://github.com/figorr/meteocat/commit/caca7a0d2bc53969db584eda2e2818321f3930fc))
* add feels like sensor ([ccecfae](https://github.com/figorr/meteocat/commit/ccecfae83f1a2e72a2438cf6a189bf5d5186d6b3))
* bump meteocatpy to 0.0.15 ([8d08b6f](https://github.com/figorr/meteocat/commit/8d08b6f66ac2ce5b029569a1538d524d3d7f50dc))

## [0.1.30](https://github.com/figorr/meteocat/compare/v0.1.29...v0.1.30) (2024-12-12)


### Bug Fixes

* 0.1.30 ([2095760](https://github.com/figorr/meteocat/commit/20957606eae28a97e82607136f97fde1abe38f81))
* add precipitation accumulated sensor ([b05090a](https://github.com/figorr/meteocat/commit/b05090a563656123464d95b17b01ba2d7cada20f))
* add precipitation_accumulated ([261d877](https://github.com/figorr/meteocat/commit/261d877cf9f68a2106687900951731ba6a4539eb))
* delete precipitation test ([845d721](https://github.com/figorr/meteocat/commit/845d721ff4e49a2fe79c5cdcf92698d52a6cff36))
* fix variables json ([df403b1](https://github.com/figorr/meteocat/commit/df403b12ab12cd357f087dc1dceda30c51e4c8f0))

## [0.1.29](https://github.com/figorr/meteocat/compare/v0.1.28...v0.1.29) (2024-12-12)


### Bug Fixes

* 0.1.29 ([f80cb9e](https://github.com/figorr/meteocat/commit/f80cb9eda9bd7d731489b51c161bc16a00ac57f0))
* bump meteocatpy to 0.0.14 ([74cc591](https://github.com/figorr/meteocat/commit/74cc591ac7e9911c77649a20088af15d3af2d350))
* remove cache ([8c4f29b](https://github.com/figorr/meteocat/commit/8c4f29b0b2c2cfa33f2b45f72bed57bf45b9a3dd))
* remove cache tests ([6082096](https://github.com/figorr/meteocat/commit/6082096a92ade5a033e0493a819b20e950aff7a3))

## [0.1.28](https://github.com/figorr/meteocat/compare/v0.1.27...v0.1.28) (2024-12-11)


### Bug Fixes

* 0.1.28 ([2c329cb](https://github.com/figorr/meteocat/commit/2c329cb960aa7bd6ec6bec0c6145db791349758f))
* bump meteocatpy to 0.0.13 ([52c11c6](https://github.com/figorr/meteocat/commit/52c11c66f66b0ebff40fea58a8a5c4d4a74482be))
* fix entity_id ([fa61841](https://github.com/figorr/meteocat/commit/fa61841ba3857a79d6b97d0e0ed12a543525c205))
* fix name sensors to include station_id ([7b868fd](https://github.com/figorr/meteocat/commit/7b868fd0eea66f8ec2655e92137d9ab6dd9d0149))
* ignore test_call_api ([976826a](https://github.com/figorr/meteocat/commit/976826a978889fcec304a8b3620ccf738e1a1946))
* save variables.json in assets folder ([d2c2234](https://github.com/figorr/meteocat/commit/d2c2234621aaabbbdc65367429b56b304855f710))
* setup cache folder and new async_remove_entry ([4dfddc0](https://github.com/figorr/meteocat/commit/4dfddc03a64f82582b39eff47870c561d0775d6d))

## [0.1.27](https://github.com/figorr/meteocat/compare/v0.1.26...v0.1.27) (2024-12-10)


### Bug Fixes

* 0.1.27 ([99feff1](https://github.com/figorr/meteocat/commit/99feff14eb85201028c1e6156a13354b05b446c3))
* bump meteocatpy to 0.0.11 ([03b9485](https://github.com/figorr/meteocat/commit/03b9485b0486a2bef7f0b7f3c0bf9bf1fca3da8c))
* bump meteocatpy to 0.0.9 ([1fb0de9](https://github.com/figorr/meteocat/commit/1fb0de97181b802494cb8371eb472a37c9a51f40))
* delete .meteocat_cache ([7941005](https://github.com/figorr/meteocat/commit/79410050e68667ca8162ff6575c0541a5f8b6207))
* fix python version ([07e3264](https://github.com/figorr/meteocat/commit/07e3264f5dde756c322ca431f4b895a211be998f))
* fix python version ([32f539b](https://github.com/figorr/meteocat/commit/32f539bb33a343881ebd26eb7ad3f12a58ecbed4))
* fix python version ([2ff2dfc](https://github.com/figorr/meteocat/commit/2ff2dfcfa597d9fbba0fc59c330f975c6b00a55b))
* ignore cache tests ([238d148](https://github.com/figorr/meteocat/commit/238d148630a5f84123f8d2d5db66dbd6e6b372f8))
* set variables cache ([ba77035](https://github.com/figorr/meteocat/commit/ba7703511c4e0604bd5d87f7d07ce487be67bafe))
* set variables cache ([ba55568](https://github.com/figorr/meteocat/commit/ba55568526fe74e83feaf4d7a0cd5127334ee139))

## [0.1.26](https://github.com/figorr/meteocat/compare/v0.1.25...v0.1.26) (2024-12-09)


### Bug Fixes

* 0.1.26 ([9d6b083](https://github.com/figorr/meteocat/commit/9d6b083205d12b628d9a62b0c8c558c0ca9d39e2))
* add station timestamp constant ([6bd0569](https://github.com/figorr/meteocat/commit/6bd0569030361b89c532ef49faae4b938c1dcf8a))
* add station timestamp sensor ([ac8b98b](https://github.com/figorr/meteocat/commit/ac8b98bcb225d1348b450b619879b6f636a213da))
* fix async_remove_entry ([ba28daa](https://github.com/figorr/meteocat/commit/ba28daa87271b6286cf22cd2bcc39422f71b668a))
* fix entity_id names ([b670d8d](https://github.com/figorr/meteocat/commit/b670d8d53888dc93f371ba7c0e4ed2cdad7ac64b))
* fix loop when saving JSON ([151dbdd](https://github.com/figorr/meteocat/commit/151dbddd932313831028e1e3e17780dd33d44640))
* sensor names ([5244f7f](https://github.com/figorr/meteocat/commit/5244f7f8e9d332bfd6adf9e65c053e4b12d8a109))

## [0.1.25](https://github.com/figorr/meteocat/compare/v0.1.24...v0.1.25) (2024-12-08)


### Bug Fixes

* 0.1.25 ([5ba0823](https://github.com/figorr/meteocat/commit/5ba0823db1da999d61c5a4d43733dff5db238ea4))
* add town and station sensors ([372383f](https://github.com/figorr/meteocat/commit/372383f1bd17ba8e385fef638cf3c1f58515dbaf))

## [0.1.24](https://github.com/figorr/meteocat/compare/v0.1.23...v0.1.24) (2024-12-08)


### Bug Fixes

* 0.1.24 ([87b8b51](https://github.com/figorr/meteocat/commit/87b8b519f78ba97a3e9fe01ac1ee85c0efd0a879))
* add function to save station_data.json ([e78d872](https://github.com/figorr/meteocat/commit/e78d872938c002fe363c2634b1d8d171ea1e2d6e))
* add solar global irradiance ([dc757b0](https://github.com/figorr/meteocat/commit/dc757b0a8df6ee971c01e290568730cdf3eb54b0))
* add solar global irradiance sensor ([d0e7373](https://github.com/figorr/meteocat/commit/d0e737302f9d7889a698468ba6ffb881d8da17c2))
* bump meteocatpy to 0.0.8 ([c280c06](https://github.com/figorr/meteocat/commit/c280c06c7c3c0703e12e94b19108537bbd03baa0))
* fix constants ([5d4e0b7](https://github.com/figorr/meteocat/commit/5d4e0b77336f1e051a04a45ccaace40ada3ed33a))

## [0.1.23](https://github.com/figorr/meteocat/compare/v0.1.22...v0.1.23) (2024-12-07)


### Bug Fixes

* 0.1.23 ([dda17ae](https://github.com/figorr/meteocat/commit/dda17ae1d73d31879d029d4c7a8f12a1a74f2379))
* fix sensor data recovery ([564ceb7](https://github.com/figorr/meteocat/commit/564ceb7ff372acd7d2d035272e9784ad583ccece))
* fix unis of measurement ([c65bce2](https://github.com/figorr/meteocat/commit/c65bce26add578bc32ebb05b82381aa72dfbf9a6))

## [0.1.22](https://github.com/figorr/meteocat/compare/v0.1.21...v0.1.22) (2024-12-07)


### Bug Fixes

* 0.1.22 ([54b39fa](https://github.com/figorr/meteocat/commit/54b39fad5e645673c2d46ca3209e82d92db03b95))
* add platforms ([fbbad49](https://github.com/figorr/meteocat/commit/fbbad49a6de960719d0c4f6a734c6dd1e0f3dfb5))
* bump meteocatpy to 0.0.7 ([f00b48d](https://github.com/figorr/meteocat/commit/f00b48da53e0f309686fa7214c60647bb0965495))
* fix coordinator to use entry_data ([5ca5050](https://github.com/figorr/meteocat/commit/5ca50501e04e8b3f6cb222f0f183dea1cc726242))
* fix UV icon ([f2c86e3](https://github.com/figorr/meteocat/commit/f2c86e3e03df987e40bdf955113f2235db347229))

## [0.1.21](https://github.com/figorr/meteocat/compare/v0.1.20...v0.1.21) (2024-12-06)


### Bug Fixes

* 0.1.21 ([a4df744](https://github.com/figorr/meteocat/commit/a4df7445f5dc05fe0a74c9d949fa551a77af6cf0))
* delete node_modules ([3b817a5](https://github.com/figorr/meteocat/commit/3b817a53c5fd6dcc44f17865f6fb39bb79c032ab))
* new repo file structure ([7ef2dbe](https://github.com/figorr/meteocat/commit/7ef2dbe67bc41c77e0f931d833578540dafe0ca8))
* semantic-release job ([a78eb5c](https://github.com/figorr/meteocat/commit/a78eb5c6dbbaef556a40053f98257906adeeecaa))


## v0.1.14 (2024-11-22)

### Bug Fixes

- 0.1.14
  ([`aca7650`](https://github.com/figorr/meteocat/commit/aca76500f09c65e50f394a23cfe48e1b3491dfbc))

- Add LICENSE
  ([`9369498`](https://github.com/figorr/meteocat/commit/93694982ed4cc4960797c095610e78b24c8dc3be))

- Ignore scripts
  ([`47dc6c4`](https://github.com/figorr/meteocat/commit/47dc6c4d29ca7c7acfdb576ad248e65cda34b9b5))

- Publish job
  ([`7b830c6`](https://github.com/figorr/meteocat/commit/7b830c63f13f60bfbb8ad8d911a10638a74fb967))

- Poetry update
  ([`aaf27ae`](https://github.com/figorr/meteocat/commit/aaf27aed177c6b94be32550a31ae4909c2c43895))

- Add aiofiles & voluptuous
  ([`2786de5`](https://github.com/figorr/meteocat/commit/2786de5ada6567c57a290979064f40fa3464aba2))

- Fix constants and placeholders
  ([`bf89109`](https://github.com/figorr/meteocat/commit/bf89109a6ea0a5cae65f86d39f4c1c24b138174c))

- Add municipis url
  ([`4815daa`](https://github.com/figorr/meteocat/commit/4815daaedec0f47b02e484d1c4dd0cb520c0044b))

- Fix repo structure
  ([`b501cad`](https://github.com/figorr/meteocat/commit/b501cad9e80911d0d75aefed8a267c6da0e519af))

- Add translations
  ([`8e849b8`](https://github.com/figorr/meteocat/commit/8e849b8a6eb13f586c13c3c27aebd98cd486a929))

- Local scripts
  ([`d2a6b72`](https://github.com/figorr/meteocat/commit/d2a6b72cba2ee64c97792c0f05b0c2a1f750d8dd))


## v0.1.13 (2024-11-20)

### Bug Fixes

- Add translations
  ([`119d539`](https://github.com/figorr/meteocat/commit/119d539d3334d4dbae8e4d13ae47639e7ccf0064))

- Fix include
  ([`56032ef`](https://github.com/figorr/meteocat/commit/56032ef488d2565e65421a556509f8e34b3fba10))

- Fix file tree structure
  ([`911ab32`](https://github.com/figorr/meteocat/commit/911ab32d625212a33e963464821b4502dfd036fa))

- Version 0.1.10
  ([`688f86d`](https://github.com/figorr/meteocat/commit/688f86da987efe8b8d429a615578d2558efdc985))

- Remove files folder
  ([`6f62ea4`](https://github.com/figorr/meteocat/commit/6f62ea48c679f5e61c93e989af86d12102185e01))

- Fix .gitignore new repository structure
  ([`f603248`](https://github.com/figorr/meteocat/commit/f603248b3d69b023a664a8d578a4771ceb34162b))

- Fix repository structure
  ([`9ef2514`](https://github.com/figorr/meteocat/commit/9ef2514be5396c11c26945024548aeec93fb50f3))

- Fix async_setup
  ([`e0605c7`](https://github.com/figorr/meteocat/commit/e0605c7f3cc3fa7b0875867f6880185684a57778))

- Jobs
  ([`43321f1`](https://github.com/figorr/meteocat/commit/43321f1f40c04d210ece3b6f3a53378d338971e5))

- Semnatic_job
  ([`5444b01`](https://github.com/figorr/meteocat/commit/5444b01bd5d89b5bfe0c85315195fb0be797e44c))

- Testing semantic_job
  ([`bb43877`](https://github.com/figorr/meteocat/commit/bb43877cab2d3e0823883efc4ca9117d0cad3b7e))

- Folder location
  ([`ea225a2`](https://github.com/figorr/meteocat/commit/ea225a24c62df29f56e33e5930d5c7af140b114f))

- Folder location
  ([`478c4f0`](https://github.com/figorr/meteocat/commit/478c4f0d8eed498789d7626851665f7c8a3357b4))

- .gitignore
  ([`0af4025`](https://github.com/figorr/meteocat/commit/0af4025312267ae9e9bb69a23126bf7ea3216fb2))

- Semantic_job git push
  ([`daa4cc0`](https://github.com/figorr/meteocat/commit/daa4cc054caddfad43c54098a807a45a1a045b92))

- Locations.py message
  ([`a05abfb`](https://github.com/figorr/meteocat/commit/a05abfb560636aef5ba3c264e2f2b0e68b637e92))

- Municipis_list name
  ([`84e0dbb`](https://github.com/figorr/meteocat/commit/84e0dbb30eade0beaf11a4b356b7654cbcc32792))

- Locations list
  ([`1abe8dc`](https://github.com/figorr/meteocat/commit/1abe8dcb8ff3558be72d9b9bf124121f19d38829))

- Semantic_job
  ([`d57c77c`](https://github.com/figorr/meteocat/commit/d57c77c8d25d09920a51f902af04ff4a95e4c7ce))

- Fix automatic version update
  ([`2708da0`](https://github.com/figorr/meteocat/commit/2708da07b53305826a2c652e7495a8c3dad79f7b))

- Fix updated_content sintaxis
  ([`3e9be4f`](https://github.com/figorr/meteocat/commit/3e9be4f3d2bee8857b9e9cb6a6b7bb254b8b544c))

- Fix version print
  ([`ebfeb99`](https://github.com/figorr/meteocat/commit/ebfeb9937e448b5b858980cde0a40a17fc56b1ef))

- Version at __init__.py
  ([`6171eaa`](https://github.com/figorr/meteocat/commit/6171eaa29d16474b3fc24bd5a2cf97db614c2d10))

- Update_version script
  ([`3c2c641`](https://github.com/figorr/meteocat/commit/3c2c6418e1aeb6f78c797302ebe15cadee9f8d6f))

- Version.py
  ([`e620c1b`](https://github.com/figorr/meteocat/commit/e620c1b4808807a3475f60708906689806ff58cd))

- Set version_variable to version.py
  ([`9a624db`](https://github.com/figorr/meteocat/commit/9a624db6b2c8efb2ec7fd93499a01ce71b2ca601))

- Disable gitlab_job
  ([`69ced63`](https://github.com/figorr/meteocat/commit/69ced63a2c5e100bc31120c29925575908f5143a))

- Fix bugs
  ([`3fe3492`](https://github.com/figorr/meteocat/commit/3fe3492ed9fc347ab52a83cafd957a7a17c59e1c))

- Fix jobs
  ([`d60ee29`](https://github.com/figorr/meteocat/commit/d60ee298a2f3efac0c253b3b1ee58ff3440974a2))

- Fix gitlab_job
  ([`d7f7c2c`](https://github.com/figorr/meteocat/commit/d7f7c2c055bfac4d6064ca2c1ae13fb1cac2e1f1))

- Fix Jobs
  ([`3d9566c`](https://github.com/figorr/meteocat/commit/3d9566c0ec75dad55973c8ca2f355902cd484f93))

- Fix semantic-release test
  ([`1ffa9d4`](https://github.com/figorr/meteocat/commit/1ffa9d4c2237898109d4794040579abb6e7a3e56))

- Fix semantic-release test
  ([`7a56521`](https://github.com/figorr/meteocat/commit/7a56521a3b7f38314894bdab61e6938dcf6dd7f3))

- Test semantic-release
  ([`7f3e017`](https://github.com/figorr/meteocat/commit/7f3e017f301cfa7d62f480050cd7875e7e9279c3))

- Fix version
  ([`ab6365a`](https://github.com/figorr/meteocat/commit/ab6365a325273589e9f14b3e3819e585d5f56bad))

- Fix gitlab_job
  ([`d11870a`](https://github.com/figorr/meteocat/commit/d11870ac9fe9ba727563fcb7515c2c0cacb0fd59))

- Fix Gitlab job
  ([`0d619fd`](https://github.com/figorr/meteocat/commit/0d619fd3d78c6081ab2db126658cbef3dc492f59))

- Fix gitlab_job
  ([`795d13b`](https://github.com/figorr/meteocat/commit/795d13b1a8706a324a732151859c8f59cabf62a8))

- Setup.py version
  ([`67699de`](https://github.com/figorr/meteocat/commit/67699de3aa561ccc0892bb83810628a1c97a65f8))

- Gitlab job
  ([`14bf324`](https://github.com/figorr/meteocat/commit/14bf32407a7222a4d8a319c17bee483ea54dfd31))

- Gitignore update
  ([`c0f949a`](https://github.com/figorr/meteocat/commit/c0f949abe67e312b6db250d04963caf06fb311eb))

- Add version.py file
  ([`7a8364b`](https://github.com/figorr/meteocat/commit/7a8364bd98c9a3cf2267a90072d1f8933b7d559e))

- Add release file
  ([`66a7c42`](https://github.com/figorr/meteocat/commit/66a7c427da442233a2b27188336272f9ced41886))

- Pypi API TOKEN
  ([`0a53bca`](https://github.com/figorr/meteocat/commit/0a53bcac4afa46f0a4b3847d8809aae75be4e31d))

- 0.1.6
  ([`378f4ee`](https://github.com/figorr/meteocat/commit/378f4eeb822dd54e6e614fe50173a8012a5b33a7))

- Add PyPi job
  ([`cdd6e48`](https://github.com/figorr/meteocat/commit/cdd6e48fbc47b2d8090425c9af800110b3188bf2))

- 0.1.4
  ([`e3028ed`](https://github.com/figorr/meteocat/commit/e3028edb0ff5f37a280616a9d24cc94165833883))

- Twine dep
  ([`3df0717`](https://github.com/figorr/meteocat/commit/3df07175ae8a807c3ab9f0ee1a1ac5421bfaa49b))

- Gh job
  ([`545034e`](https://github.com/figorr/meteocat/commit/545034e7cbbd38417247e6c21d99d1be93ab6b28))

- Fix push to GH
  ([`5db9892`](https://github.com/figorr/meteocat/commit/5db989256b06ec5e94edd3c8825a8e26758a45cc))

- Virtual env
  ([`62852bf`](https://github.com/figorr/meteocat/commit/62852bff62585b22744651515f58ded7ffa02515))

- Fix Bugs
  ([`0dbd7dc`](https://github.com/figorr/meteocat/commit/0dbd7dc15ce12d100151dedf1ace7f8415f7a819))

- 0.1.3
  ([`009e9b6`](https://github.com/figorr/meteocat/commit/009e9b62ce459334ad5aed1b36061e8a059577f3))

- Fix Jobs
  ([`47ef9ae`](https://github.com/figorr/meteocat/commit/47ef9ae50c6a8f092afbff6b26cfb4bcd384a579))

- Fix GitHub Job
  ([`59114e2`](https://github.com/figorr/meteocat/commit/59114e273294f63abd7072eb39278c5b819bc56a))

- Update README
  ([`c29929e`](https://github.com/figorr/meteocat/commit/c29929e572969cff2ae07cdc56b4812e169ac7de))

- Fix semantic-release
  ([`2d2c192`](https://github.com/figorr/meteocat/commit/2d2c1928445eb65199a7f8693d5fad8bd81770fd))

- Fix Jobs
  ([`15ec59b`](https://github.com/figorr/meteocat/commit/15ec59b068cd27de73fe89b7f5e2143f79d52e9b))

- Fix version job
  ([`7317949`](https://github.com/figorr/meteocat/commit/7317949f6c6cbc8ea7933b6d6c8567b431bd3924))

- Fix version_job
  ([`278d896`](https://github.com/figorr/meteocat/commit/278d896480df2c13e8ff17657fd1fe5935e2e363))

- Fix version_job
  ([`a0fdd80`](https://github.com/figorr/meteocat/commit/a0fdd80233129c40a424d8dde509444da105e0a9))

- Fix semantic-release no-push
  ([`5fedeaa`](https://github.com/figorr/meteocat/commit/5fedeaab3ef2516ccc781cccd091971b43a165e8))

- Fix version_job
  ([`010252a`](https://github.com/figorr/meteocat/commit/010252a8506b43649dcdc2bdafc8e8c0af95e363))

- Fix semantic-release master
  ([`2638433`](https://github.com/figorr/meteocat/commit/26384332a90e41b1e8e1bfd63e0eba66f270ee09))

- Fix version_job
  ([`56459f6`](https://github.com/figorr/meteocat/commit/56459f6bb581c41fde69d1cc2bcc8a85181de749))

- Fix version_job
  ([`b825a5c`](https://github.com/figorr/meteocat/commit/b825a5cbba56f27bc4474c226a010d9d5a9c3bff))

- Fix semantic-release
  ([`82e90a4`](https://github.com/figorr/meteocat/commit/82e90a45af3cbe6432d3a8b7532607fb7d819734))

- Gitlab release Job
  ([`35e05f9`](https://github.com/figorr/meteocat/commit/35e05f9e0067104563260ff34e340c0bb4d89aa3))

- Fix authentication
  ([`af5c349`](https://github.com/figorr/meteocat/commit/af5c349f51bbfad972250840b1b81451389a4f4b))

- Fix job bugs
  ([`11c169a`](https://github.com/figorr/meteocat/commit/11c169a05b348dd5cb7fb9a3281e541323dd2a1f))

- Fix Jobs
  ([`2d7204a`](https://github.com/figorr/meteocat/commit/2d7204a7e95ea75db0bed7dd63f096039f4af9a2))

- Fix bugs
  ([`52f3c0f`](https://github.com/figorr/meteocat/commit/52f3c0f34016c8a8002e2356bf60c85c32548c7f))

- Fix jobs
  ([`c9d5d3f`](https://github.com/figorr/meteocat/commit/c9d5d3fea8659cca9ef3c05f8a99e576ed75c4d5))

- Fix jobs
  ([`6cbfcaa`](https://github.com/figorr/meteocat/commit/6cbfcaae0344da0981f66703001ef69b047ba3ef))

- Fix script
  ([`ebcf377`](https://github.com/figorr/meteocat/commit/ebcf377afc020865329ed601ff21bb07991487b0))

- Fix variables
  ([`6c28da8`](https://github.com/figorr/meteocat/commit/6c28da86ab60d441fe7cc2a923cefec805b25f77))

- Fix semantic-release
  ([`2ab754e`](https://github.com/figorr/meteocat/commit/2ab754e9f65a346f188b6ca57a8043503eee7b6d))

- Fix semantic-release
  ([`162685b`](https://github.com/figorr/meteocat/commit/162685b2c1fd692802ac4d18bda7b394bbdf9a72))

- Create .releaserc for semantic-release
  ([`8d1859b`](https://github.com/figorr/meteocat/commit/8d1859b928964ed16d83c26de42c179a1597af53))

- Fix release_job
  ([`60c4d19`](https://github.com/figorr/meteocat/commit/60c4d19afd2a65944267bb9c25c7f62f39cc7ebb))

- Update release job
  ([`0070caf`](https://github.com/figorr/meteocat/commit/0070caff7cc1c9ddbf11b03d63380f6a3375cde4))

- Delete deploy job
  ([`69b049c`](https://github.com/figorr/meteocat/commit/69b049cc53ab62ddd45636e0bc5f5886561093ee))

- Fix Jobs
  ([`ff9ac05`](https://github.com/figorr/meteocat/commit/ff9ac05f34db29d0cfd69c25f82b2f7ad916bfd7))

- Delete deploy_job
  ([`756f399`](https://github.com/figorr/meteocat/commit/756f399280bcf4a66c36bcc19bdceeeb25e25a60))

- Fix release job
  ([`877ced7`](https://github.com/figorr/meteocat/commit/877ced7453d7656cc9f406efc73cffd10cb31d13))

- Automatic upload to PyPi
  ([`ef35667`](https://github.com/figorr/meteocat/commit/ef35667c560cff73674881f4463918626abdce7f))

- Fix release job
  ([`4dda574`](https://github.com/figorr/meteocat/commit/4dda574b4828f3cccd3238b18fe26e4a4940a7fc))

- Fix release job
  ([`e8b5dd2`](https://github.com/figorr/meteocat/commit/e8b5dd2ba8d09905e010f3003e22a73b7f6bf1d3))

- Fix python-semantic-release version
  ([`a539aa0`](https://github.com/figorr/meteocat/commit/a539aa04afea83b084e07bbd44ee89adbd9247c2))

- Fix bump_and_publish job
  ([`c6bf435`](https://github.com/figorr/meteocat/commit/c6bf435e69f01d2f48d86206fb03b06f48e41d90))

- Release
  ([`d485379`](https://github.com/figorr/meteocat/commit/d4853794f10a9fd3f7f64f68656791617d38cd3a))

- Fix release_job
  ([`5246274`](https://github.com/figorr/meteocat/commit/5246274cbecda1ff345e10c2f53b8d4c347a3954))

- Fix release_job
  ([`e42cdb8`](https://github.com/figorr/meteocat/commit/e42cdb8d3139739249422ef2ca5e9dd65cfcd745))

- Fix release_job
  ([`cd8417a`](https://github.com/figorr/meteocat/commit/cd8417a182746ec09194ab147b974b7e412b2501))

- Fix release_job
  ([`4b7f17c`](https://github.com/figorr/meteocat/commit/4b7f17c9715ef0d79f1d29b96750df96b380c906))

- Fix release_job
  ([`5ab7774`](https://github.com/figorr/meteocat/commit/5ab77745a963dc57c65e69306be2f68d43260f69))

- Release_job
  ([`acc447e`](https://github.com/figorr/meteocat/commit/acc447e2b3bdcc864e670e9796ac43342a2091cf))

- Manual install Python 3 and pip
  ([`b6070f4`](https://github.com/figorr/meteocat/commit/b6070f41fd5aa94ca005213d831a6ca39b5203ca))

- Add node:20
  ([`2acafeb`](https://github.com/figorr/meteocat/commit/2acafeb30af036e6fd83fa286def41de4a2b0a8e))

- Delete requirements.txt
  ([`a5cf2e0`](https://github.com/figorr/meteocat/commit/a5cf2e0c379b646abf09b563f7ad3db1bbf42951))

- _logger import
  ([`0f4dc39`](https://github.com/figorr/meteocat/commit/0f4dc39144d5897da223111d1c8783eef5a4d6f8))

- Update locations.py folder location
  ([`d7113d5`](https://github.com/figorr/meteocat/commit/d7113d52e40161c6439ee9f20bda20ee3b302c77))

- Setup semantic-release
  ([`933c360`](https://github.com/figorr/meteocat/commit/933c36068fc86fca7da77c361f632511d0f2c5db))

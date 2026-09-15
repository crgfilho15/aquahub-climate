# AquaHub Climate Platform

## Methodological Questions for Research Team

### Purpose

This document summarises the main scientific and technical decisions that should be confirmed before expanding the current AquaHub climate-processing prototype to future climate scenarios, additional variables, bioclimatic indices and agroclimatic zoning.

The current prototype already validates:

- CHELSA raster processing;
- CAOP administrative boundaries;
- fractional pixel coverage;
- area-weighted zonal statistics;
- monthly climatologies;
- annual climatological aggregation;
- municipality processing;
- NUTS III regional processing;
- reproducible Parquet outputs;
- automated scientific and software tests.

The questions below concern the **definitive scientific methodology** of the AquaHub climatic and agroclimatic atlas.

---

## 1. Scope of the work

1. Is my responsibility focused specifically on the **climatic/agroclimatic atlas**, or should I also contribute to the socioeconomic diagnosis described in Activity A.1.1?

2. Should the climate-processing workflow cover the complete AquaHub intervention area from the beginning?

Current project regions include:

- Trás-os-Montes e Alto Douro;
- Beira Interior;
- Castilla y León;
- Extremadura.

3. Should the first implementation remain focused on Portugal before expanding to Spain?

---

## 2. Spatial resolution and geographic outputs

4. Is the main scientific product expected to remain at approximately **1 km spatial resolution**?

5. Should administrative summaries also be generated for:

- municipality;
- NUTS III;
- NUTS II;
- intervention region?

6. Should municipality values be considered mainly an **interaction/dashboard layer**, while the ~1 km raster remains the main scientific product?

7. Should the atlas cover the complete territory or only agricultural/crop-relevant areas?

8. Will a crop or agricultural land-use mask be provided, or should one be identified from external datasets?

---

## 3. Historical climate dataset

9. Which dataset should be considered the definitive historical/baseline climate source?

Possible options currently identified include:

- CHELSA climatologies;
- CHELSA-W5E5;
- another dataset defined by the research team.

10. Should the AquaHub methodology follow the same historical dataset strategy used in the MONTEVITIS reference work?

11. Is **1981–2010** the definitive historical reference period?

If not, which climatological baseline should be used?

---

## 4. Future climate dataset

12. Which dataset should be used for future climate projections?

For example:

- CHELSA-ISIMIP3b;
- CHELSA climatology future products;
- another downscaled CMIP6 dataset.

13. Should the future methodology follow the CHELSA-ISIMIP3b approach used in the MONTEVITIS reference?

---

## 5. Future climate periods

14. Which future climatological periods should be presented?

Possible examples:

```text
2041–2070
2071–2100
```

or:

```text
2041–2060
2081–2100
```

15. Are both a medium-term and long-term period required?

---

## 6. SSP scenarios

16. Which SSP scenarios should be included?

The MONTEVITIS reference uses:

```text
SSP1-2.6
SSP3-7.0
SSP5-8.5
```

Should AquaHub use the same scenarios?

17. Should an intermediate scenario such as SSP2-4.5 also be considered?

---

## 7. Global Climate Models

18. Which GCMs should be included?

Should AquaHub use the same nine models considered in the MONTEVITIS methodology?

Possible reference set:

```text
CanESM5
CNRM-CM6-1
CNRM-ESM2-1
EC-Earth3
IPSL-CM6A-LR
MIROC6
MPI-ESM1-2-LR
MRI-ESM2-0
UKESM1-0-LL
```

19. Should individual GCM results remain available to researchers, or should the platform primarily expose the ensemble result?

---

## 8. Multi-model ensemble

20. What should be the main ensemble statistic?

Possible options:

- arithmetic mean;
- median;
- another methodology.

21. How should model uncertainty be represented?

Possible options include:

- minimum and maximum;
- standard deviation;
- inter-model range;
- percentiles;
- confidence intervals.

22. Should uncertainty information appear directly in the public platform or only in advanced/research outputs?

---

## 9. Climate variables

23. Which variables are mandatory for the AquaHub atlas?

Possible variables include:

```text
tas
tasmin
tasmax
pr
```

Potential additional variables may include:

- evapotranspiration;
- water balance;
- drought-related variables.

24. Should monthly climatologies be preserved for all variables?

25. Should the interface provide:

- annual values;
- seasonal values;
- monthly values;
- all three?

---

## 10. Climate-change indicators

26. Should future conditions be shown only as absolute climate values, or also as anomalies relative to the baseline?

For temperature, for example:

```text
future temperature - historical temperature
```

27. For precipitation, should change be represented as:

- absolute difference;
- percentage change;
- both?

---

## 11. Bioclimatic indices

28. Which bioclimatic indices should be calculated for each crop?

The project documentation identifies crops such as:

- vineyard;
- olive;
- almond;
- cherry.

29. Are the indices already defined by the AquaHub team, or should they be selected from scientific literature?

30. Should we follow or adapt indices used in the MONTEVITIS work?

Potential examples include:

- Growing Degree Days;
- Winkler Index;
- Huglin Index;
- Cool Night Index;
- Dryness Index;
- De Martonne Index;
- growing-season temperature;
- growing-season precipitation;
- extreme-temperature indicators.

---

## 12. Crop-specific thresholds

31. Are agroclimatic suitability thresholds already defined for each crop?

32. If not, should thresholds be identified through literature review and subsequently validated by crop experts within the project?

33. Should suitability be represented using classes such as:

```text
unsuitable
marginal
suitable
highly suitable
```

or using another classification system?

---

## 13. Agroclimatic zoning

34. How should multiple climate and bioclimatic indicators be combined into the final agroclimatic zoning?

35. Should zoning be produced separately for:

```text
vineyard
olive
almond
cherry
```

36. Should the zoning represent:

- current suitability;
- future suitability;
- suitability change;
- all three?

---

## 14. Validation

37. Which observational or reference datasets should be used to validate the climate information?

Possible sources may include:

- meteorological stations;
- ERA5;
- E-OBS;
- national meteorological datasets.

38. Is a formal quantitative validation required before the atlas outputs are published?

39. Which validation metrics should be used?

---

## 15. Platform users and interaction

40. Who are the main expected users?

Possible groups:

- farmers;
- researchers;
- public administration;
- agricultural technicians;
- project partners.

41. Should the interface have different levels of complexity for different users?

For example:

```text
simple mode
→ municipality + climate indicator + scenario

advanced mode
→ GCM + SSP + period + variable + uncertainty
```

42. Should users be able to click a municipality or geographic region and obtain its climatological summary?

43. Should individual ~1 km raster cells also be queryable?

---

## 16. Data export

44. Which outputs should users be able to download?

Possible formats:

- CSV;
- XLSX;
- GeoTIFF;
- GeoPackage;
- PNG/PDF maps.

45. Should researchers have access to the underlying model-level data, while general users receive only ensemble products?

---

## 17. Prototype strategy

46. Is the following development strategy scientifically appropriate?

```text
Step 1
Historical baseline + tas

Step 2
One future period + one SSP + one GCM

Step 3
Multiple GCMs

Step 4
Multi-model ensemble

Step 5
Additional climate variables

Step 6
Bioclimatic indices

Step 7
Crop-specific agroclimatic zoning

Step 8
Interactive platform
```

47. Is **Douro** an appropriate region for the first complete regional prototype before scaling to all AquaHub intervention areas?

---

## Priority questions for the next development stage

The most urgent decisions before continuing large-scale climate-data processing are:

```text
1. Historical dataset
2. Future dataset
3. Historical reference period
4. Future periods
5. SSP scenarios
6. GCM selection
7. Ensemble methodology
8. Required climate variables
9. Required bioclimatic indices
10. Agroclimatic thresholds
11. Final spatial extent
12. Validation methodology
```

Until these items are confirmed, the current CHELSA `tas` 1981–2010 workflow should remain the validated technical baseline rather than being treated as the definitive AquaHub methodology.
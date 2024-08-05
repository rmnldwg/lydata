# 2021 USZ Oropharynx

[![Greeen Journal](https://img.shields.io/badge/Rad%20Onc-j.radonc.2022.01.035-3e6e0e)][Radiotherapy & Oncology]
[![medRxiv](https://img.shields.io/badge/medR%CF%87iv-2021.12.01.21267001-0e4c92)][medRxiv]
[![Data in Brief](https://img.shields.io/badge/DiB-10.1016%2Fj.dib.2022.108345-orange)][Data in Brief]
[![Zenodo DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.5833835-informational)][zenodo]

This folder contains the detailed patterns of lymphatic progression of 287 patients with squamous cell carcinomas (SCCs) in the oropharynx, treated at the University Hospital Zurich (USZ) between 2013 and 2019.

You can find here

* the data itself as `data.csv`
* a citation file `CITATION.cff` that can be used to cite this dataset. But it is also possible to cite the [Data in Brief] paper or the [zenodo] identifier.
* a jupyter notebook `figures.ipynb` for rendering figures visualizing different aspects of the data
* the folder `figures` containing the already rendered figures which we also used in our publication for *Radiation & Oncology* [[1]](#1).

## Cohort Characteristics

Below we show some figures that aim to coarsely characterize the patient cohort in this directory.

| ![age distribution](figures/age_and_sex.png)                               |
| ---------------------------------------------------------------------------- |
| **Figure 1:** *Distribution over age, stratified by sex and smoking status.* |

| ![T-category distribution](figures/t_category.png)                         | ![subsite distribution](figures/subsite.png)           |
| ---------------------------------------------------------------------------- | -------------------------------------------------------- |
| **Figure 2:** *Distribution over age, stratified by sex and smoking status.* | **Figure 3:** *Distribution over primary tumor subsite.* |

## Curation

We have detailed inclusion criteria and what was considered lymphatic involvement in our paper that has been published in the journal of [Radiotherapy & Oncology] (a preprint is also available on [medRxiv]). The data of this repository is also - and in somewhat more detail - described and provided in its own publication in [Data in Brief], enabling anyone to reuse and cite our dataset.

## Online Interface

We provide a user-friendly and intuitive graphical user interface to view the dataset, which is available at <https://2021-oropharynx.lyprox.org/>. The GUI has two main functionalities: the patient list and the dashboard. The patient list allows for viewing the characteristics of a patient, corresponding to one row of the csv file, in a visually appealing and intuitive way. The dashboard allows for filtering of the dataset. For example, the user may select all patients with primary tumors extending over the mid-sagittal plane with involvement of ipsilateral level III. The dashboard will then display the number or percentage of patients with metastases in each of the other LNLs.

## Description

The data is provided as a CSV-table containing one row for each of the 287 patients. The table has a header with three levels that describe the columns. Below we explain each column in the form of a list with three levels. So, for example, list entry 1.i.g refers to a column with the three-level header `patient | # | hpv_status` and underneath it tha patients' HPV status is listed.

## Columns

1. **`patient:`** General information about the patient’s condition can be found under this top-level header.
    1. **`#:`** The second level under patient has no meaning and exists solely as a filler.
        1. **`id:`** Enumeration of the patients
        2. **`institution:`** The clinic at which the patient were treated and recorded. This holds the value "University Hospital Zurich" for all patients in this dataset.
        3. **`sex:`** Sex of the patient
        4. **`age:`** Patient’s age at diagnosis
        5. **`diagnose_date:`** Date of diagnosis (format `YYYY-mm-dd`) defined as the date of first histological confirmation of HNSCC.
        6. **`alcohol_abuse:`** `true` for patients who stated that they consume alcohol regularly, `false` otherwise
        7. **`nicotine_abuse:`** `true` for patients who have been regular smokers (> 10 pack years)
        8. **`hpv_status:`** `true` for patients with human papilloma virus associated tumors (as defined by p16 immunohistochemistry)
        9. **`neck_dissection:`** Indicates whether the patient has received a neck dissection as part of the treatment.
        10. **`tnm_edition:`** The edition of the TNM classification used to classify the patient [[2]](#2)
        11. **`n_stage:`** Degree of spread to regional lymph nodes
        12. **`m_stage:`** Presence of distant metastases
2. **`tumor:`** Information about tumors is stored under this top-level header
    1. **`<number>:`** The second level enumerates the synchronous tumors. In our database, no patient has had a second tumor, but this structure of the file allows us to include such patients in the future. The third-level headers are the same for each tumor.
        1. **`location:`** Anatomic location of the tumor
        2. **`subsite:`** ICD-O-3 code associated with a tumor at the particular location according to the world health organization [[3]](#3), [[4]](#4)
        3. **`side:`** Lateralization of the tumor. Can be `“left”` or `“right”` for tumors that have their center of mass clearly on the respective side of the mid-sagittal line and `“central”` for patients with a tumor on the mid-sagittal line.
        4. **`central:`** Whether the tumor is centralized or not.
        5. **`extension:`** True if part of the tumor extends over the mid-sagittal line
        6. **`volume:`** Volume of the tumor in cm3
        7. **`stage_prefix:`** Prefix modifier of the T-category. Can be `“c”` or `“p”`
        8. **`t_stage:`** T-category of the tumor, according to TNM staging
3. **`<diagnostic modality>:`** Each recorded diagnostic modality is indicated by its own top-level header. In this file FNA, CT, MRI, PET, pathology and pCT (planning CT) are provided
    1. **`info:`**
        1. **`date:`** Day on which a diagnose with the respective modality was performed
    2. **`ipsi:`** All findings of involved lymph nodes on the ipsilateral side of the patient’s neck
        1. **`<LNL>:`** One column is provided for each recorded lymph node level. For each level `true` indicates at least one finding diagnosed as malignant lymph node in the respective LNL, `false` means no malignant lymph node has been found and an empty field indicates that no diagnosis is available for this LNL according to the respective diagnostic modality. `<LNL>` can be: I, Ia, Ib, II, IIa, IIb, III, IV, V, VI, VII, VIII, IX, X.
    3. **`contra:`** Same as 3.ii but for the contralateral side of the patient’s neck
        1. **`<LNL>:`** same as under 3.ii.a

## References

<a id="1">[1]</a>
R. Ludwig, B. Pouymayou, J.-M. Hoffmann *et al*,
"Detailed patient-individual reporting of lymph node involvement in oropharyngeal squamous cell carcinoma with an online interface."
Radiotherapy & Oncology, 2021, DOI: [10.1016/j.radonc.2022.01.035][Radiotherapy & Oncology]

<a id="2">[2]</a>
J. D. Brierley, M. K. Gospodarowicz, and C. Wittekind,
"TNM Classification of Malignant Tumours."
John Wiley & Sons, 2017.

<a id="3">[3]</a>
World Health Organization, Ed.,
"International statistical classification of diseases and related health problems, 10th revision, 2nd edition."
Geneva: World Health Organization, 2004.

<a id="4">[4]</a>
A. G. Fritz, Ed.,
"International classification of diseases for oncology: ICD-O, 3rd ed."
Geneva: World Health Organization, 2000.

[Radiotherapy & Oncology]: https://doi.org/10.1016/j.radonc.2022.01.035
[Data in Brief]: https://doi.org/10.1016/j.dib.2022.108345
[medRxiv]: https://doi.org/10.1101/2021.12.01.21267001
[zenodo]: https://doi.org/10.5281/zenodo.5833835

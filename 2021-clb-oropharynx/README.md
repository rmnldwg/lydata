# 2021 CLB Oropharynx

> :warning: **WARNING**  
> This is not yet finalized.

[![Green Journal](https://img.shields.io/badge/Rad%20Onc-j.radonc.2021.01.028-3e6e0e)](https://doi.org/10.1016/j.radonc.2021.01.028)

This folder contains the detailed patterns of lymphatic progression of 263 patients with squamous cell carcinomas (SCCs) in the oropharynx, treated at the Centre Léon Bérard (CLB) between 2014 and 2018.

## Curation

This is detailed in their publication [[1]](#1) and a we are planning to submit a manuscript describing the data the *Data in Brief* journal.


## Description

The data is provided as a CSV-table containing one row for each of the 287 patients. The table has a header with three levels that describe the columns. Below we explain each column in the form of a list with three levels. So, for example, list entry 1.i.g refers to a column with the three-level header `patient | # | hpv_status` and underneath it tha patients' HPV status is listed.


## Columns

1. **`patient:`** General information about the patient’s condition can be found under this top-level header.
    1. **`#:`** The second level under patient has no meaning and exists solely as a filler.
        1. **`id:`** Enumeration of the patients
        2. **`institution:`** The clinic where the data was extracted.
        3. **`sex:`** Sex of the patient
        4. **`age:`** Patient’s age at diagnosis
        5. **`diagnose_date:`** Date of diagnosis (format `YYYY-mm-dd`) defined as the date of first histological confirmation of HNSCC.
        6. **`alcohol_abuse:`** `true` for patients who stated that they consume alcohol regularly, `false` otherwise
        7. **`nicotine_abuse:`** `true` for patients who have been regular smokers (> 10 pack years)
        8. **`pack_years:`** Number of pack years of smoking hitory of the patient
        9. **`hpv_status:`** `true` for patients with human papilloma virus associated tumors (as defined by p16 immunohistochemistry)
        10. **`neck_dissection:`** Indicates whether the patient has received a neck dissection as part of the treatment.
        11. **`tnm_edition:`** The edition of the TNM classification used to classify the patient [[2]](#2)
        12. **`n_stage:`** Degree of spread to regional lymph nodes
        13. **`m_stage:`** Presence of distant metastases
2. **`tumor:`** Information about tumors is stored under this top-level header
    1. **`<number>:`** The second level enumerates the synchronous tumors. In our database, no patient has had a second tumor, but this structure of the file allows us to include such patients in the future. The third-level headers are the same for each tumor.
        1. **`location:`** Anatomic location of the tumor
        2. **`subsite:`** ICD-O-3 code associated with a tumor at the particular location according to the world health organization [[3]](#3), [[4]](#4)
        3. **`central:`** Whether the tumor is centralized or not.
        4. **`extension:`** True if part of the tumor extends over the mid-sagittal line
        5. **`volume:`** Volume of the tumor in cm3
        6. **`stage_prefix:`** Prefix modifier of the T-category. Can be `“c”` or `“p”`
        7. **`t_stage:`** T-category of the tumor, according to TNM staging
3. **`<diagnostic modality>:`** Each recorded diagnostic modality is indicated by its own top-level header. In this file `diagnostic_consensus` and `pathology` are provided.
    1. **`info:`** 
        1. **`date:`** Day on which a diagnose with the respective modality was performed
    2. **`ipsi:`** All findings of involved lymph nodes on the ipsilateral side of the patient’s neck
        1. **`<LNL>:`** One column is provided for each recorded lymph node level. For each level `true` indicates at least one finding diagnosed as malignant lymph node in the respective LNL, `false` means no malignant lymph node has been found and an empty field indicates that no diagnosis is available for this LNL according to the respective diagnostic modality. `<LNL>` can be: I, Ia, Ib, II, IIa, IIb, III, IV, V, VI, VII, VIII, IX, X.
    3. **`contra:`** Same as 3.ii but for the contralateral side of the patient’s neck
        1. **`<LNL>:`** same as under 3.ii.a
4. **`total_dissected:`** The number of dissected lymph nodes per LNL.
   1. **`info:`**
      1. **`date:`** Day on which the neck dissection was performed
   2. **`ipsi:`** Number of dissected lymph nodes from the LNLs on the ipsilateral side of the neck
      1. **`<LNL>:`** One column is provided for each recorded lymph node level. For each level a non-negative integer indicates the number of lymph nodes that were dissected in the respective `<LNL>`. A missing entry indicates that the LNL was not resected.
   3. **`contra:`** Same as 4.ii, but for the contralateral side of the neck
      1. **`<LNL>:`** Same as under 4.ii.a
5. **`positive_dissected:`** The number of dissected lymph nodes that were found to harbour metastases per LNL.
   1. **`info:`**
      1. **`date:`** Day on which the neck dissection was performed
   2. **`ipsi:`** Number of pathologically involved lymph nodes from the LNLs on the ipsilateral side of the neck
      1. **`<LNL>:`** One column is provided for each recorded lymph node level. For each level a non-negative integer indicates the number of lymph nodes that were found to harbour malignant disease in the respective `<LNL>`. A missing entry indicates that the LNL was not resected.
   3. **`contra:`** Same as 5.ii, but for the contralateral side of the neck
      1. **`<LNL>:`** Same as under 5.ii.a


## Online Interface

We provide a user-friendly and intuitive graphical user interface to view the dataset, which is available at https://lyprox.org/. The GUI has two main functionalities: the patient list and the dashboard. The patient list allows for viewing the characteristics of a patient, corresponding to one row of the csv file, in a visually appealing and intuitive way. The dashboard allows for filtering of the dataset. For example, the user may select all patients with primary tumors extending over the mid-sagittal plane with involvement of ipsilateral level III. The dashboard will then display the number or percentage of patients with metastases in each of the other LNLs.


## References

<a id="1">[1]</a>
L. Bauwens *et al*, "Prevalence and distribution of cervical lymph node metastases in HPV-positive and HPV-negative oropharyngeal squamous cell carcinoma", Radiotherapy & Oncology, 2021, DOI: [10.1016/j.radonc.2021.01.028](https://doi.org/10.1016/j.radonc.2021.01.028)

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

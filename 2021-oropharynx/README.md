## Data description

The data is provided as a CSV-table containing one row for each of the 287 patients. The table has a header with three levels that describe the columns. Below we explain each column in the form of a list with three levels.

## Columns

1. **`patient:`** General information about the patient’s condition can be found under this top-level header.
    1. **`#:`** The second level under patient has no meaning and exists solely as a filler.
        1. **`id:`** Enumeration of the patients
        1. **`sex:`** Sex of the patient
        1. **`age:`** Patient’s age at diagnosis
        1. **`diagnose_date:`** Date of diagnosis (format `YYYY-mm-dd`) defined as the date of first histological confirmation of HNSCC.
        1. **`alcohol_abuse:`** `true` for patients who stated that they consume alcohol regularly, `false` otherwise
        1. **`nicotine_abuse:`** `true` for patients who have been regular smokers (> 10 pack years)
        1. **`hpv_status:`** `true` for patients with human papilloma virus associated tumors (as defined by p16 immunohistochemistry)
        1. **`neck_dissection:`** Indicates whether the patient has received a neck dissection as part of the treatment.
        1. **`tnm_edition:`** The edition of the TNM classification used to classify the patient [6]
        1. **`n_stage:`** Degree of spread to regional lymph nodes
        1. **`m_stage:`** Presence of distant metastases
2. **`tumor:`** Information about tumors is stored under this top-level header
    1. **`<number>:`** The second level enumerates the synchronous tumors. In our database, no patient has had a second tumor, but this structure of the file allows us to include such patients in the future. The third-level headers are the same for each tumor.
        1. **`location:`** Anatomic location of the tumor
        1. **`subsite:`** ICD-O-3 code associated with a tumor at the particular location according to the world health organization [7], [8]
        1. **`side:`** Lateralization of the tumor. Can be `“left”` or `“right”` for tumors that have their center of mass clearly on the respective side of the mid-sagittal line and `“central”` for patients with a tumor on the mid-sagittal line.
        1. **`extension:`** True if part of the tumor extends over the mid-sagittal line
        1. **`volume:`** Volume of the tumor in cm2
        1. **`stage_prefix:`** Prefix modifier of the T-category. Can be `“c”` or `“p”`
        1. **`t_stage:`** T-category of the tumor, according to TNM staging
3. **`<diagnostic modality>:`** Each recorded diagnostic modality is indicated by its own top-level header. In this file FNA, CT, MRI, PET, path (pathology) and pCT (planning CT) are provided
    1. **`info:`** 
        1. **`date:`** Day on which a diagnose with the respective modality was performed
    1. **`right:`** All findings of involved lymph nodes on the right side of the patient’s neck
        1. **`<LNL>:`** One column is provided for each recorded lymph node level. For each level `true` indicates at least one finding diagnosed as malignant lymph node in the respective LNL, `false` means no malignant lymph node has been found and an empty field indicates that no diagnosis is available for this LNL according to the respective diagnostic modality. `<LNL>` can be: I, Ia, Ib, II, IIa, IIb, III, IV, V, VI, VII, VIII, IX, X.
    1. **`left:`** Same as b) but for the left side of the patient’s neck
        1. **`<LNL>:`** same as under 3)b)i)

## Online Interface

We provide a user-friendly and intuitive graphical user interface to view the dataset, which is available at https://2021-oropharynx.lyprox.org/. The GUI has two main functionalities: the patient list and the dashboard. The patient list allows for viewing the characteristics of a patient, corresponding to one row of the csv file, in a visually appealing and intuitive way. The dashboard allows for filtering of the dataset. For example, the user may select all patients with primary tumors extending over the mid-sagittal plane with involvement of ipsilateral level III. The dashboard will then display the number or percentage of patients with metastases in each of the other LNLs.
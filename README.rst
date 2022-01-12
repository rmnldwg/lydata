.. image:: ./github-social-card.png

.. image:: https://zenodo.org/badge/423488981.svg
   :target: https://zenodo.org/badge/latestdoi/423488981


What is lyDATA?
===============

lyDATA is a repository for datasets that report detailed patterns of lymphatic progression for head & neck squamous cell carcinoma (HNSCC).


Motivation
==========

HNSCC spreads though the lymphatic system of the neck and forms metastases in regional lymph nodes. Macroscopic metastases can be detected with imaging modalities like MRI, PET and CT scans. They are then consequently included in the target volume, when radiotherapy is chosen as part of the treatment. However, microscopic metastases are too small be diagnosed with current imaging techniques.

To account for this microscopic involvement, parts of the lymphatic system are often irradiated electively to increase tumor control. Which parts are included in this elective clinical target volume is curretnly decided based on guidelines like [1]_, [2]_, [3]_ and [4]_. These in turn are derived from reports of the prevalence of involvement per lymph node level (LNL), i.e. the portion of patients that were diagnosed with metastases in any given LNL, stratified by primary tumor location. It is recommended to include a LNL in the elective target volume if 10 - 15% of patients showed involvement in that particular level.

However, while the prevalence of involvement has been reported in the literature, e.g. in [5]_ and [6]_, and the general lymph drainage pathways are understood well, the detailed progression patterns of HNSCC remain poorly quantified. We believe that the risk for microscopic involvement in an LNL depends highly on the specific diagnose of a particular patient and their treatment can hence be personalized if the progression patterns were better quantified.


Our Goal
========

In this repository we aim to provide data on the detailed lymphatic progression patterns extracted from patients of the University Hospital Zurch (USZ). The data can be used freely and we hope clincians in the field find it useful as well. Ideally, we can motivate other researchers to share their data in similar detail and openness, so that large multicentric datasets can be built.


Available datasets
==================

2021 oropharynx
---------------

The first dataset we are able to share consists of 287 patients with a primary tumor in the oropharynx, treated at our institution between 2013 and 2019. It can be found in the folder ``2021-oropharynx`` alongside a ``jupyter`` notebook that was used to create figures.

We have submitted a paper on it to *Radiother & Oncology* and make this data available through a *Data in Brief* paper as well. We will update this section and link to the publications, as soon as they are accepted.

stay tuned for more...
----------------------

We are in the process of collecting more data of patients with primary tumors in other locations.


Attribution
===========

Every folder that corresponds to a dataset also contains a ``CITATION.cff`` file which may be used to cite the respective dataset. To cite the entire repository with all datasets inside, use the ``CITATION.cff`` at the root of the repository (or just click the *Cite this repository* button on the right).


See also
========

LyProX Interface
----------------

The data in this repository can be explored interactively in our online interface `LyProX <https://lyprox.org>`_ `(GitHub repo) <https://github.com/rmnldwg/lyprox>`_.


Probabilistic models
--------------------

We have developed and implemented probabilistic models for lymphatic tumor progression ([7]_, [8]_) that may allow for highly personalized risk predictions in the future. These models can be trained using the dataset(s) in this repository. For details on the implementation, check out the `lymph <https://github.com/rmnldwg/lymph>`_ package.


References
==========

.. [1] Vincent Grégoire and Others, "Selection and delineation of lymph node target volumes in head and neck conformal radiotherapy. Proposal for standardizing terminology and procedure based on the surgical experience", Radiother. Oncol., vol. 56, pp. 135–150, 2000, doi: https://doi.org/10.1016/S0167-8140(00)00202-4.
.. [2] Vincent Grégoire, A. Eisbruch, M. Hamoir, and P. Levendag, "Proposal for the delineation of the nodal CTV in the node-positive and the post-operative neck", Radiotherapy and Oncology, vol. 79, no. 1, pp. 15–20, Apr. 2006, doi: https://doi.org/10.1016/j.radonc.2006.03.009.
.. [3] Vincent Grégoire et al., "Delineation of the neck node levels for head and neck tumors: A 2013 update. DAHANCA, EORTC, HKNPCSG, NCIC CTG, NCRI, RTOG, TROG consensus guidelines", Radiotherapy and Oncology, vol. 110, no. 1, pp. 172–181, Jan. 2014, doi: https://doi.org/10.1016/j.radonc.2013.10.010.
.. [4] Julian Biau et al., "Selection of lymph node target volumes for definitive head and neck radiation therapy: a 2019 Update", Radiotherapy and Oncology, vol. 134, pp. 1–9, May 2019, doi: https://doi.org/10.1016/j.radonc.2019.01.018.
.. [5] Jatin. P. Shah, F. C. Candela, and A. K. Poddar, "The patterns of cervical lymph node metastases from squamous carcinoma of the oral cavity", Cancer, vol. 66, no. 1, pp. 109–113, 1990, doi: https://doi.org/10.1002/1097-0142(19900701)66:1<109::AID-CNCR2820660120>3.0.CO;2-A.
.. [6] Laurence Bauwens et al., "Prevalence and distribution of cervical lymph node metastases in HPV-positive and HPV-negative oropharyngeal squamous cell carcinoma", Radiother Oncol, vol. 157, pp. 122–129, Apr. 2021, doi: https://doi.org/10.1016/j.radonc.2021.01.028.
.. [7] Bertrand Pouymayou, P. Balermpas, O. Riesterer, M. Guckenberger, and J. Unkelbach, "A Bayesian network model of lymphatic tumor progression for personalized elective CTV definition in head and neck cancers", Physics in Medicine & Biology, vol. 64, no. 16, p. 165003, Aug. 2019, doi: https://doi.org/10.1088/1361-6560/ab2a18.
.. [8] Roman Ludwig, B. Pouymayou, P. Balermpas, and J. Unkelbach, "A hidden Markov model for lymphatic tumor progression in the head and neck", Sci Rep, vol. 11, no. 1, p. 12261, Dec. 2021, doi: https://doi.org/10.1038/s41598-021-91544-1.

Perkin Elmer Winlab32

Written for PinAAcle 900H and Optima 8300, it may need some refactoring for other
instruments and configurations than those tested.

The file can be XLS, XLSX, or CSV.

Three column values are used, which must have the headers below.  Other columns are ignored

    - Sample ID
    - Analyte Name
    - Reported Conc (Calib)

The interim fields on the analysis service (or calculation) will be completed as follows:

    - `reading`: Contains the value from the Analyte Name column for this sample

`Sample ID` and `Analyte Name` will be used to locate the destination analysis for each result. They will be transformed
before searching like this:

    - `Sample ID`: Only letters, numbers, dashes and underscores will remain.
    - `Analyte Name`: Only letters and numbers will remain.

If a cell value contains multiple lines of text, only the first line will be imported.

`Analyte name` does not need to contain an exact match to the AnalysisService keyword.

        - If `Analyte Name` column contains a value "Ag 107 (cps)" the AR must contain 
          one Analysis who's keyword starts with "Ag107cps".

        - If exactly one such analyses is not found, the record is skipped with a warning.


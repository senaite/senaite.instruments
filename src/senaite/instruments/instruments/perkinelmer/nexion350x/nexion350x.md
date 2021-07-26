Perkin Elmer Nexion 350X
========================

The file can be XLS, XLSX, or CSV.

There are two required columns in the incoming data, other columns are ignored

    - "Sample ID"
    - 1+ column headers containing analyte names

The interim fields on the calculation will be completed as follows:

    - `reading`: Contains the value from the Analyte Name column for this sample

`Sample ID` and column headers containing analyte names, will be used to locate the destination sample and analysis for
each result. They will be transformed before searching:

    - `Sample ID`: Only letters, numbers, dashes and underscores will remain.
    - analyte name column header: Only letters and numbers will remain.

If a cell value contains multiple lines of text, only the first line will be imported.

The analyte name column header values do not need to contain exact matches:

    - If the analyte column header contains a value "Ag 107" then the sample
      must contain one Analysis who's keyword starts with "Ag107".

    - If exactly one such analyses is not found, the record is skipped with a warning.


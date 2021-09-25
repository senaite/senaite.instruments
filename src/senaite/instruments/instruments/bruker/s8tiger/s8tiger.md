Bruker S8 Importer

The AR and Sample are found using the base filename of the provided file, possibly accounting for the -9digit suffix.
The file must be XLS, XLSX, or CSV format, and it's columns are mapped to interim fields like this:

    Column heading          Interim field
    --------------          -------------
    - Formula               formula
    - Concentration         concentration
    - Z                     z
    - Status                status
    - Line 1                line_1
    - Net int.              net_int
    - LLD                   lld
    - Stat. error           stat_error
    - Analyzed layer        analyzed_layer
    - Bound %               bound_pct

Additional calculation interim fields are populated:

    - 'reading_ppm': `concentration` in numeric form, represented as PPM
    - 'reading_pct': `concentration` in numeric form, represented as a percentage.
    - 'reading':  `concentration` value in units selected at import.

If no calculation is selected, the `reading` value is used as the default result for the analysis.

`Formula` column is used to discover the Analysis Service which should receive the values.

    - `Formula` column does not need to contain an exact match to the AnalysisService keyword.
    
        - If `Formula` value is "Fe2O3", then the AR must contain one Analysis who's keyword
          starts with "Fe203".

        - If exactly one such analyses is not found, the record is skipped with a warning.

The remaining columns are written to their interim fields, if these fields exist.


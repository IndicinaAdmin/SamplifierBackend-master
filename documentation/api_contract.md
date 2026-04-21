# Calculus
* Oversamples object
  
  The oversample set for each measure in the calculation export page
```
{
  CBP: float
  CSS: float
  CDC: float
  COA: float
  CIS: float
  COL: float
  IMA: float
  LSC: float
  PPC: float
  TRC: float
  WCC: float
}
```
**Note:** Oversamples objects will have a subset of the attributes listed above. Each Product Line has a different set of measures

* PreprocessedMrsss object

  The calculated MRSSs for each measure in the submission file.
```
{
  CBP: float
  CSS: float
  CDC: float
  COA: float
  CIS: float
  COL: float
  IMA: float
  LSC: float
  PPC: float
  TRC: float
  WCC: float
}
```
**Note:** PreprocessedMrsss objects will have a subset of the attributes listed above. Each Product Line has a different set of measures

* OutputMetadata object

  The metadata of a submission file that should be displayed in the output page and included in the exported files.
```
{
  audited: bool
  organizationName: string
  productLine: string
  specialProject: string
  reportingProduct: string
  organizationId: string
  submissionId: string
}
```
**Note:** According to requirement 49 of *Functional Requirements Lis.docx* the submission file may have a blank SpecialProject attribute, and, in these cases, the output page should display an empty line where the SpecialProject would be placed. Therefore, in these cases, the back-end will return an empty string as the SpecialProduct value (i.e., `specialProject: ""`).  

* SubmissionStatus object
```
{
  sKey: string
  status: string
  errorMessage: string
  oldTimestamp: int
  preProcessedMrsss: <preprocessed_mrss_object>,
  outputMetadata: <output_metadata_object>,
}
```
**Note1:** The possible values for the status attribute are:
- "INVALID"
- "VALID"
- "WRONG_CALC_KEY"
- "CALCULATED"
- "UNEXPECTED_ERROR"
- "EXPORTED"

**Note2:** The `oldTimestamp` is only present in Wrong Timestamp responses.

**GET /calc/filestatus/:file_id**
----
  Gets the status of submission file.
* **URL Params**  
  *Required:* `user_id=[string]`  
  *Required:* `file_id=[string]`  
  **Note:** `file_id` has the format:  
  `<MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml`
* **Data Params**  
  None
* **Malformed `file_submission_id` Response:**  
* **Code:** 400  
**Content:**  
  None  
* **Unauthorized Response:**  
* **Code:** 401  
**Content:**  
  None  
* **Validated Response:**  
* **Code:** 200  
  **Content:**  
```
{<submission_status_object>}
```
* **File Not Found Response:**  
* **Code:** 404  
  **Content:**  
```
{errorMessage: "File not found"}
```
* **Invalid File Response:**  
* **Code:** 406  
  **Content:**  
```
{<submission_status_object>}
```
* **Wrong Timestamp Response:**  
* **Code:** 409  
  **Content:**  
```
{<submission_status_object>}
```
* **Calculated Response:**  
* **Code:** 202  
  **Content:**  
```
{<submission_status_object>}
```
* **Calculus Error Response:**  
* **Code:** 500  
  **Content:**  
```
{<submission_status_object>}
```
* **Exported Response:**  
* **Code:** 201  
  **Content:**  
```
{<submission_status_object>}
```
* **Export Error Response:**  
* **Code:** 500  
  **Content:**  
```
{<submission_status_object>}
```

**POST /calc/configuration/:file_id**
----
  Start the calculus for an already uploaded file.
* **URL Params**  
  *Required:* `user_id=[string]`  
  *Required:* `file_id=[string]`  
  **Note:** `file_id` has the format:  
  `<MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml`
* **Data Params**  
```
{
  measurementYear: integer
  combine: [
    [combination1Measure1, combination1Measure2],
    [combination2Measure1, combination2Measure2]
  ]
}
```
* **Success Response:** 
* **Code:** 200  
  **Content:**
```
{
  preProcessedMrsss: <preprocessed_mrss_object>
  outputMetadata: <output_metadata_object>
}
```
* **Malformed `file_submission_id` Response:**  
* **Code:** 400  
  **Content:**  
  None
* **Unauthorized Response:**  
* **Code:** 401  
**Content:**  
  None  
* **File Not Found Response:**  
* **Code:** 404  
  **Content:** `{ errorMessage : "Submission file not found" }`
* **General Error Response:**  
* **Code:** 500  
  **Content:** `{ errorMessage : <error_message> }`

**POST /calc/exportcsv/:user_id/:file_submission_id**
----
  Exports the calculus result with the FSS in a csv file and saves the selected oversamples in a json file on S3.  
* **URL Params**  
  *Required:* `user_id=[string]`  
  *Required:* `file_submission_id=[string]`  
  **Note1:** `file_submission_id` has the format  
  `<MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml`
  
* **Data Params**  
```
{
  oversamples: <oversamples_object>
}
```
* **Success Response:**  
* **Code:** 201  
  **Content:**  
  None  
* **Malformed `file_submission_id` Response:**  
* **Code:** 400  
**Content:**  
  None  
* **Unauthorized Response:**  
* **Code:** 401  
**Content:**  
  None  
* **File Not Found Response:**  
* **Code:** 404  
  **Content:** `{ errorMessage : "Submission file not found" }`
* **General Error Response:**  
* **Code:** 500  
  **Content:** `{ errorMessage : <error_message> }`
  
**POST /calc/oversamples/:user_id/:file_submission_id**
----
  Saves the selected oversamples in a json file on S3.  
* **URL Params**  
  *Required:* `user_id=[string]`  
  *Required:* `file_submission_id=[string]`  
  **Note1:** `file_submission_id` has the format  
  `<MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml`
  
* **Data Params**  
```
{
  oversamples: <oversamples_object>
}
```
* **Success Response:**  
* **Code:** 201  
  **Content:**  
  None  
* **Malformed `file_submission_id` Response:**  
* **Code:** 400  
**Content:**  
  None  
* **Unauthorized Response:**  
* **Code:** 401  
**Content:**  
  None  
* **File Not Found Response:**  
* **Code:** 404  
  **Content:** `{ errorMessage : "Submission file not found" }`
* **General Error Response:**  
* **Code:** 500  
  **Content:** `{ errorMessage : <error_message> }`

# User
**GET /user/allow-new-upload/:user_id/**
----
  To check if the user has not uploaded a file in the last 3 seconds and therefore is allowed to upload a new file.
* **URL Params**  
  *Required:* `user_id=[string]`
* **Data Params**  
  None
* **Upload Allowed Response:**  
* **Code:** 200  
  **Content:**  
  None 
* **Too soon Error:**  
* **Code:** 429  
  **Content:** `{ waitTime : <time_to_wait_in_seconds> }`
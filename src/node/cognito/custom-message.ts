import * as lambda from "aws-lambda";
import * as AWS from "aws-sdk";

/**
 * Gets a StringList parameter from SSM and returns it as an String[]
 * @param ssm an SSM instance
 * @param name the parameter name
 * @return a String[] with the StringList parameter values
 */
async function getStringListParameter(
    ssm: AWS.SSM,
    name?: string
): Promise<string[]> {
    if (!name) throw "parameter name cannot be null or undefined";
    let options = {
        Name: name,
        WithDecryption: true,
    };
    // Debug level logs were disabled
    // console.debug(`recovering parameter: ${name}`);
    return await ssm
        .getParameter(options)
        .promise()
        .then((data) => {
            if (
                !(
                    data.Parameter?.Value &&
                    data.Parameter?.Type &&
                    data.Parameter.Type === "StringList"
                )
            )
                throw "error to get parameter";
            return data.Parameter.Value.toString().split(",");
        })
        .catch((err) => {
            console.error(err);
            throw err;
        });
}

/**
 * Builds the HTML for the email confirmation message using the provided parameters.
 * @param indicinaLogoLink a URL link to the Indicina logo
 * @param samplifierLogoLink a URL link to the Samplifier logo
 * @param userDisplayName the name the client should be addressed by in the email
 * @param confirmationLink a link to confirm the user's email address
 * @param tosLink a link to Samplifier's Terms of Service pdf
 * @param privacyPolLink a link to Samplifier's Privacy Policy pdf
 * @returns a string containing the HTML code for the message
 */
function buildConfirmationEmail(
    indicinaLogoLink: string,
    samplifierLogoLink: string,
    userDisplayName: string,
    confirmationLink: string,
    tosLink: string,
    privacyPolLink: string
): string {
    const response = `<html><head>

    <meta name="viewport" content="initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no, width=device-width">
    <!--[if !mso]><!-- -->
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <!--<![endif]-->
    <title>Validate your email address</title>
    <style type="text/css">
        body {
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif;
        }
        table, td {
        border-collapse: collapse !important;
        mso-table-lspace: 0pt;
        mso-table-rspace: 0pt;
        }
        img {
        outline: none;
        text-decoration: none;
        -ms-interpolation-mode: bicubic;
        }
        a {
        color: inherit;
        outline: none;
        text-decoration: none;
        }
        * {
        text-size-adjust: none;
        -webkit-text-size-adjust: none;
        -moz-text-size-adjust: none;
        -ms-text-size-adjust: none;
        -webkit-font-smoothing: antialiased;
        }
        .ReadMsgBody, .ExternalClass {
        width: 100%;
        }
        .ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div {
        line-height: 100%;
        }
    </style>
    <style type="text/css">
        @media only screen and (max-width: 600px) {
        *[class="gmail-fix"] {
        display: none !important;
        }
        }
    </style>
    <style type="text/css">
        a[x-apple-data-detectors] {
        color: inherit !important;
        text-decoration: none !important;
        font-size: inherit !important;
        font-family: inherit !important;
        font-weight: inherit !important;
        line-height: inherit !important;
        }
        div[style*="margin: 16px 0"] {
        margin: 0 !important;
        }
    </style>
    <style type="text/css">
        @media screen and (max-width: 600px) {
        .p100 {
        width: 100% !important;
        }
        .p90 {
        width: 90% !important;
        }
        .p95 {
        width: 95% !important;
        }
        .p90auto {
        width: 90% !important;
        height: auto !important;
        }
        .p80 {
        width: 80% !important;
        }
        .p50 {
        width: 50% !important;
        }
        .hide {
        width: 0 !important;
        display: none !important;
        }
        .p100auto {
        width: 100% !important;
        height: auto !important;
        }
        .hauto {
        height: auto !important;
        }
        .align-center {
        alignment-adjust: center !important;
        text-align: center !important;
        }
        .mobilecontent {
        display: block !important;
        overflow: visible !important;
        max-width: inherit !important;
        max-height: inherit !important;
        }
        .dglogo {
        width: auto !important;
        height: 35px !important;
        }
        .h40 {
        height: 40px !important;
        }
        .w260{
        width:260px !important;
        }
        a[class="cta-button"] {
        display: block !important;
        margin: 0 15px !important;
        border-right: 30px solid #0A93D3 !important;
        border-left: 30px solid #0A93D3 !important;
        text-align: center !important;
    }
}
    </style>
</head>
<body style="width:100% !important; background-color: #f6f6f6;">
    <table cellpadding="0" cellspacing="0" border="0" width="100%" align="center" bgcolor="#f6f6f6">
        <!-- gmail fixes -->
        <tr>
            <td class="gmail-fix" align="center">
                <table cellpadding="0" cellspacing="0" border="0" align="center" width="680">
                    <tr>
                        <td cellpadding="0" cellspacing="0" border="0" height="1" style="line-height: 1px; min-width: 680px;" align="center"><img src="images/20170816_DG_gmail.gif" width="680" height="1" style="display: block; max-height: 1px; min-height: 1px; min-width: 680px; width: 680px;"></td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td>
                <div style="display:none; white-space:nowrap; font:15px courier; line-height:0;"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
                    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
                    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
                </div>
            </td>
        </tr>
        <!-- gmail fixes eneded--><!-- //////////////////////// divider ////////////////////////-->
        <tr>
            <td height="20">&nbsp;</td>
        </tr>
        <!-- //////////////////////// divider ////////////////////////-->
        <tr>
            <td align="center">
                <div style="max-width: 600px; margin:auto;">
                    <!-- Start of Main Layout -->
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" align="center">
                        <tr>
                            <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" border="0" align="center" class="p100" bgcolor="#f6f6f6">
                                    <tr>
                                        <td align="center">
                                            <table width="560" cellpadding="0" cellspacing="0" border="0" align="center" class="p100">
                                                <tr>
                                                    <td align="left">
                                                        <!-- --><!-- -->
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                    <!-- End of Main Layout -->
                </div>
                <!-- End of postfooter --><!--[if (gte mso 9)|(IE)]>
            </td>
        </tr>
    </table>
    <![endif]--></td>
    </tr>
    <tr>
        <td align="center">
            <div style="max-width: 600px; margin:auto;">
                <!-- Start of Main Layout -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" align="center">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" border="0" align="center" class="p100" bgcolor="#f6f6f6">
                                <tr>
                                    <td align="center">
                                        <table width="560" cellpadding="0" cellspacing="0" border="0" align="center" class="p100">
                                            <tr>
                                                <td align="center">
                <table cellpadding="0" cellspacing="0" border="0" width="116" class="p100" align="center">
<tr>
<td align="center"><table cellpadding="0" cellspacing="0" border="0" width="116" align="center">
  <tr>
    <td align="center"><a href="https://www.samplifier.app/" target="_blank"><img src="${samplifierLogoLink}" alt="Samplifier" width="230" height="51" style="display:block; border:none; outline:none; text-decoration:none; color:#000000; font-weight: bold; font-size: 22px;" border="0"></a></td>
  </tr>
</table></td>
</tr>
</table></td>
                                            </tr>
<tr>
    <td align="center" height="25">&nbsp;</td>
  </tr>
<tr>
    <td align="center" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#333333; font-size:24px; line-height:30px;">Verify your email address</td>
  </tr>
<tr>
    <td align="center" height="20">&nbsp;</td>
  </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
                <!-- End of Main Layout -->
            </div>
            <!-- End of postfooter --><!--[if (gte mso 9)|(IE)]>
        </td>
    </tr>
    </table>
    <![endif]--></td>
    </tr>
    <tr>
        <td align="center">
            <div style="max-width: 600px; margin:auto;">
                <!-- Start of Main Layout -->
                <table width="600" cellpadding="0" cellspacing="0" border="0" align="center" class="p90" bgcolor="#ffffff">
                    <tr>
                        <td align="center">
                            <table width="530" cellpadding="0" cellspacing="0" border="0" align="center" class="p90">
                                <tr>
                                    <td align="center">
                                        <table cellpadding="0" cellspacing="0" border="0" width="530" align="center" class="p90">
<tr>
  <td height="30">&nbsp;</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px;padding-bottom: 15px;">Hello ${userDisplayName},</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px; padding-bottom: 15px;">Thank you for registering an account with Samplifier. Please click on the link to <a href="${confirmationLink}" target="_blank" style="color:#0A93D3; text-decoration: underline">verify your email address</a>.</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px;padding-bottom: 15px;">If you did not register with Samplifier, you can ignore this email.</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px; padding-bottom: 15px;">Please <a href="https://indicina.com/contact-us" target="_blank" style="color:#0A93D3; text-decoration: underline">contact us</a> with any questions, we're always happy to assist you.</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px;padding-bottom: 15px;">Cheers,</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px;">Indicina</td>
</tr>
</table>
                                    </td>
                                </tr>
                                <tr class="p80">
                                    <td height="30">&nbsp;</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
                <!-- End of Main Layout -->
            </div>
            <!-- End of postfooter --><!--[if (gte mso 9)|(IE)]>
        </td>
    </tr>
    </table>
    <![endif]--></td>
    </tr>
    <!-- //////////////////////// divider ////////////////////////--><!-- divider --><!-- divider ends -->
    <tr>
        <td align="center" bgcolor="#f6f6f6">
            <!-- Start of Required Outlook Specific Code when using multicolumn layouts.
                gte mso 9 targets Outlook clients greater than or equal to Outlook 2000,
                these code fragments are used in multiple places throughout the template and
                these must be left within a comment to work properly --><!--[if (gte mso 9)|(IE)]>
            <table width="680" align="center" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td valign="top">
                        <![endif]-->
                        <!-- End of Required Outlook Preheader --><!-- div element to handle Apple Mail and Outlook 2011 ignoring the max-width style on table elements -->


                <div style="max-width: 600px; margin:auto;">
<!-- Start of Main Layout -->
   <table width="100%" cellpadding="0" cellspacing="0" border="0" align="center" bgcolor="#f6f6f6">
     <tr>
       <td align="center"><table width="600" cellpadding="0" cellspacing="0" border="0" align="center" class="p90">
         <tr>
           <td height="30">&nbsp;</td>
         </tr>
         <tr>
           <td align="center" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#333333; font-size:12px; line-height:18px;">Samplifier © 2021. All Rights Reserved.</td>
         </tr>
         <tr>
           <td width="100%" height="20" style="line-height: 10px; font-size: 0px; mso-line-height-rule:exactly;"></td>
         </tr>
         <tr>
         <td style="text-align: center; vertical-align: top; font-size: 0;"
             align="center">
             <!-- Start of left column -->
             <table align="center" style="text-align: center;" class="p100">
                 <tbody align="center" style="display: inline-block">
                     <tr class="p100" style="display: inline-block">
                         <td align="center" class="p100" width="100"><a href="${tosLink}"
                                 target="_blank"
                                 style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#333333; font-size:12px; line-height:22px; text-decoration: underline; white-space: nowrap;">Terms&nbsp;of&nbsp;service</a></td>
                     </tr>
                     <tr class="p100" style="display: inline-block">
                         <td align="center" class="p100" width="100"><a
                                 href="${privacyPolLink}" target="_blank"
                                 style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#333333; font-size:12px; line-height:22px;text-decoration: underline; white-space: nowrap;">Privacy&nbsp;policy</a></td>
                     </tr>
                 </tbody>
             </table>
             <!-- End of left column -->
         </td>
     </tr>
 <tr><td>
           </td></tr>
         <tr>
           <td width="100%" height="20" style="line-height: 10px; font-size: 0px; mso-line-height-rule:exactly;"></td>
         </tr>
         <tr>
           <td align="center"><a href="https://indicina.com/" target="_blank"><img src="${indicinaLogoLink}" alt="Indicina" width="170" height="122.5" style="display:block; border:none; outline:none; text-decoration:none; color:#000000; font-weight: bold; font-size: 22px;" border="0"></a></td>
         </tr>
         <tr>
           <td align="center" height="30">&nbsp;</td>
         </tr>
</table></td>
      </tr>
    </table>
     <!-- End of Main Layout -->
</div>



<!-- End of postfooter --><!--[if (gte mso 9)|(IE)]>
                        </td>
                        </tr>
                        </table>
                        <![endif]-->
                    </td>
                </tr>
            </table>
</body>
</html>`;

    return response;
}

/**
 * Builds the HTML for a password reset email using the provided parameters.
 * @param indicinaLogoLink a URL link to the Indicina logo
 * @param samplifierLogoLink a URL link to the Samplifier logo
 * @param userDisplayName the name the client should be addressed by in the email
 * @param passwordResetLink a link to confirm the user's email address
 * @param tosLink a link to Samplifier's Terms of Service pdf
 * @param privacyPolLink a link to Samplifier's Privacy Policy pdf
 * @returns a string containing the HTML code for the message
 */
function buildPasswordResetEmail(
    indicinaLogoLink: string,
    samplifierLogoLink: string,
    userDisplayName: string,
    passwordResetLink: string,
    tosLink: string,
    privacyPolLink: string
): string {
    const response = `<html><head>

    <meta name="viewport" content="initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no, width=device-width">
    <!--[if !mso]><!-- -->
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <!--<![endif]-->
    <title>Reset your Samplifier password</title>
    <style type="text/css">
        body {
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif;
        }
        table, td {
        border-collapse: collapse !important;
        mso-table-lspace: 0pt;
        mso-table-rspace: 0pt;
        }
        img {
        outline: none;
        text-decoration: none;
        -ms-interpolation-mode: bicubic;
        }
        a {
        color: inherit;
        outline: none;
        text-decoration: none;
        }
        * {
        text-size-adjust: none;
        -webkit-text-size-adjust: none;
        -moz-text-size-adjust: none;
        -ms-text-size-adjust: none;
        -webkit-font-smoothing: antialiased;
        }
        .ReadMsgBody, .ExternalClass {
        width: 100%;
        }
        .ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div {
        line-height: 100%;
        }
    </style>
    <style type="text/css">
        @media only screen and (max-width: 600px) {
        *[class="gmail-fix"] {
        display: none !important;
        }
        }
    </style>
    <style type="text/css">
        a[x-apple-data-detectors] {
        color: inherit !important;
        text-decoration: none !important;
        font-size: inherit !important;
        font-family: inherit !important;
        font-weight: inherit !important;
        line-height: inherit !important;
        }
        div[style*="margin: 16px 0"] {
        margin: 0 !important;
        }
    </style>
    <style type="text/css">
        @media screen and (max-width: 600px) {
        .p100 {
        width: 100% !important;
        }
        .p90 {
        width: 90% !important;
        }
        .p95 {
        width: 95% !important;
        }
        .p90auto {
        width: 90% !important;
        height: auto !important;
        }
        .p80 {
        width: 80% !important;
        }
        .p50 {
        width: 50% !important;
        }
        .hide {
        width: 0 !important;
        display: none !important;
        }
        .p100auto {
        width: 100% !important;
        height: auto !important;
        }
        .hauto {
        height: auto !important;
        }
        .align-center {
        alignment-adjust: center !important;
        text-align: center !important;
        }
        .mobilecontent {
        display: block !important;
        overflow: visible !important;
        max-width: inherit !important;
        max-height: inherit !important;
        }
        .dglogo {
        width: auto !important;
        height: 35px !important;
        }
        .h40 {
        height: 40px !important;
        }
        .w260{
        width:260px !important;
        }
        a[class="cta-button"] {
        display: block !important;
        margin: 0 15px !important;
        border-right: 30px solid #0A93D3 !important;
        border-left: 30px solid #0A93D3 !important;
        text-align: center !important;
    }
}
    </style>
</head>
<body style="width:100% !important; background-color: #f6f6f6;">
    <table cellpadding="0" cellspacing="0" border="0" width="100%" align="center" bgcolor="#f6f6f6">
        <!-- gmail fixes -->
        <tr>
            <td class="gmail-fix" align="center">
                <table cellpadding="0" cellspacing="0" border="0" align="center" width="680">
                    <tr>
                        <td cellpadding="0" cellspacing="0" border="0" height="1" style="line-height: 1px; min-width: 680px;" align="center"><img src="images/20170816_DG_gmail.gif" width="680" height="1" style="display: block; max-height: 1px; min-height: 1px; min-width: 680px; width: 680px;"></td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td>
                <div style="display:none; white-space:nowrap; font:15px courier; line-height:0;"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
                    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
                    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
                </div>
            </td>
        </tr>
        <!-- gmail fixes eneded--><!-- //////////////////////// divider ////////////////////////-->
        <tr>
            <td height="20">&nbsp;</td>
        </tr>
        <!-- //////////////////////// divider ////////////////////////-->
        <tr>
            <td align="center">
                <div style="max-width: 600px; margin:auto;">
                    <!-- Start of Main Layout -->
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" align="center">
                        <tr>
                            <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" border="0" align="center" class="p100" bgcolor="#f6f6f6">
                                    <tr>
                                        <td align="center">
                                            <table width="560" cellpadding="0" cellspacing="0" border="0" align="center" class="p100">
                                                <tr>
                                                    <td align="left">
                                                        <!-- --><!-- -->
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                    <!-- End of Main Layout -->
                </div>
                <!-- End of postfooter --><!--[if (gte mso 9)|(IE)]>
            </td>
        </tr>
    </table>
    <![endif]--></td>
    </tr>
    <tr>
        <td align="center">
            <div style="max-width: 600px; margin:auto;">
                <!-- Start of Main Layout -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" align="center">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" border="0" align="center" class="p100" bgcolor="#f6f6f6">
                                <tr>
                                    <td align="center">
                                        <table width="560" cellpadding="0" cellspacing="0" border="0" align="center" class="p100">
                                            <tr>
                                                <td align="center">
                <table cellpadding="0" cellspacing="0" border="0" width="116" class="p100" align="center">
<tr>
<td align="center"><table cellpadding="0" cellspacing="0" border="0" width="116" align="center">
  <tr>
    <td align="center"><a href="https://www.samplifier.app/" target="_blank"><img src="${samplifierLogoLink}" alt="Samplifier" width="230" height="51" style="display:block; border:none; outline:none; text-decoration:none; color:#000000; font-weight: bold; font-size: 22px;" border="0"></a></td>
  </tr>
</table></td>
</tr>
</table></td>
                                            </tr>
<tr>
    <td align="center" height="25">&nbsp;</td>
  </tr>
<tr>
    <td align="center" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#333333; font-size:24px; line-height:30px;">Reset password</td>
  </tr>
<tr>
    <td align="center" height="20">&nbsp;</td>
  </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
                <!-- End of Main Layout -->
            </div>
            <!-- End of postfooter --><!--[if (gte mso 9)|(IE)]>
        </td>
    </tr>
    </table>
    <![endif]--></td>
    </tr>
    <tr>
        <td align="center">
            <div style="max-width: 600px; margin:auto;">
                <!-- Start of Main Layout -->
                <table width="600" cellpadding="0" cellspacing="0" border="0" align="center" class="p90" bgcolor="#ffffff">
                    <tr>
                        <td align="center">
                            <table width="530" cellpadding="0" cellspacing="0" border="0" align="center" class="p90">
                                <tr>
                                    <td align="center">
                                        <table cellpadding="0" cellspacing="0" border="0" width="530" align="center" class="p90">
<tr>
  <td height="30">&nbsp;</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px;padding-bottom: 15px;">Hello ${userDisplayName},</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px; padding-bottom: 15px;">You are receiving this email because you asked to reset your Samplifier password.</td>
</tr>
<tr>
    <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px; padding-bottom: 15px;">Please click on the link to <a href="${passwordResetLink}" target="_blank" style="color:#0A93D3; text-decoration: underline">Reset password</a>.</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px;padding-bottom: 15px;">If you don't want to reset your Samplifier password, you can ignore this email.</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px; padding-bottom: 15px;">Please <a href="https://indicina.com/contact-us" target="_blank" style="color:#0A93D3; text-decoration: underline">contact us</a> with any questions, we're always happy to assist you.</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px;padding-bottom: 15px;">Cheers,</td>
</tr>
<tr>
  <td align="left" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#000000; font-size:14px; line-height:22px;">Indicina</td>
</tr>
</table>
                                    </td>
                                </tr>
                                <tr class="p80">
                                    <td height="30">&nbsp;</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
                <!-- End of Main Layout -->
            </div>
            <!-- End of postfooter --><!--[if (gte mso 9)|(IE)]>
        </td>
    </tr>
    </table>
    <![endif]--></td>
    </tr>
    <!-- //////////////////////// divider ////////////////////////--><!-- divider --><!-- divider ends -->
    <tr>
        <td align="center" bgcolor="#f6f6f6">
            <!-- Start of Required Outlook Specific Code when using multicolumn layouts.
                gte mso 9 targets Outlook clients greater than or equal to Outlook 2000,
                these code fragments are used in multiple places throughout the template and
                these must be left within a comment to work properly --><!--[if (gte mso 9)|(IE)]>
            <table width="680" align="center" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td valign="top">
                        <![endif]-->
                        <!-- End of Required Outlook Preheader --><!-- div element to handle Apple Mail and Outlook 2011 ignoring the max-width style on table elements -->


                <div style="max-width: 600px; margin:auto;">
<!-- Start of Main Layout -->
   <table width="100%" cellpadding="0" cellspacing="0" border="0" align="center" bgcolor="#f6f6f6">
     <tr>
       <td align="center"><table width="600" cellpadding="0" cellspacing="0" border="0" align="center" class="p90">
         <tr>
           <td height="30">&nbsp;</td>
         </tr>
         <tr>
           <td align="center" style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#333333; font-size:12px; line-height:18px;">Samplifier © 2021. All Rights Reserved.</td>
         </tr>
         <tr>
           <td width="100%" height="20" style="line-height: 10px; font-size: 0px; mso-line-height-rule:exactly;"></td>
         </tr>
         <tr>
         <td style="text-align: center; vertical-align: top; font-size: 0;"
             align="center">
             <!-- Start of left column -->
             <table align="center" style="text-align: center;" class="p100">
                 <tbody align="center" style="display: inline-block">
                     <tr class="p100" style="display: inline-block">
                         <td align="center" class="p100" width="100"><a href="${tosLink}"
                                 target="_blank"
                                 style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#333333; font-size:12px; line-height:22px; text-decoration: underline; white-space: nowrap;">Terms&nbsp;of&nbsp;service</a></td>
                     </tr>
                     <tr class="p100" style="display: inline-block">
                         <td align="center" class="p100" width="100"><a
                                 href="${privacyPolLink}" target="_blank"
                                 style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color:#333333; font-size:12px; line-height:22px;text-decoration: underline; white-space: nowrap;">Privacy&nbsp;policy</a></td>
                     </tr>
                 </tbody>
             </table>
             <!-- End of left column -->
         </td>
     </tr>
 <tr><td>
           </td></tr>
         <tr>
           <td width="100%" height="20" style="line-height: 10px; font-size: 0px; mso-line-height-rule:exactly;"></td>
         </tr>
         <tr>
           <td align="center"><a href="https://indicina.com/" target="_blank"><img src="${indicinaLogoLink}" alt="Indicina" width="170" height="122.5" style="display:block; border:none; outline:none; text-decoration:none; color:#000000; font-weight: bold; font-size: 22px;" border="0"></a></td>
         </tr>
         <tr>
           <td align="center" height="30">&nbsp;</td>
         </tr>
</table></td>
      </tr>
    </table>
     <!-- End of Main Layout -->
</div>



<!-- End of postfooter --><!--[if (gte mso 9)|(IE)]>
                        </td>
                        </tr>
                        </table>
                        <![endif]-->
                    </td>
                </tr>
            </table>
</body>
</html>`;
    return response;
}

/**
 * Handles the Cognito event to send an email message
 * @param event the Cognito event
 */
export const handler = async (
    event: lambda.CustomMessageTriggerEvent
): Promise<lambda.CustomMessageTriggerEvent> => {
    let appMetadata:any = {
        "action": "SendConfirmationLinkEmail"
    };
    try {
        let link = "";

        // Get parameters from the event
        const { codeParameter } = event.request;
        const { userName, region } = event;
        const escapedFirstName = event.request.userAttributes.given_name;
        const { clientId } = event.callerContext;
        const { email } = event.request.userAttributes;

        // Debug level logs were disabled
        // console.debug(event);
        appMetadata["cognito-user-sub"] = event.request.userAttributes.sub;

        // An SSM instance
        const ssm = new AWS.SSM({ region: "us-east-1" });

        const ssmDomainNamesParameter = await getStringListParameter(
            ssm,
            "/samplifier/frontend/domain/names"
        );

        // Debug level logs were disabled
        // console.debug(JSON.stringify({ ssmDomainNamesParameter: ssmDomainNamesParameter }));

        const domainName = ssmDomainNamesParameter[0];

        const baseUrl = `https://${domainName}`;

        const indicinaLogo = `${baseUrl}/files/email/indicinaLogo.png`;
        const samplifierLogo = `${baseUrl}/files/email/samplifierLogo.png`;
        const tosLink = `${baseUrl}/files/docs/Samplifier Terms of Service.pdf`;
        const privacyPolLink = `${baseUrl}/files/docs/Samplifier Privacy Policy.pdf`;

        // Debug level logs were disabled
        // console.debug(JSON.stringify({ baseUrl: baseUrl }));

        if (event.triggerSource === "CustomMessage_SignUp") {
            link = `${baseUrl}?code=${codeParameter}&username=${userName}&clientId=${clientId}&region=${region}&email=${email}`;
            // Debug level logs were disabled
            // console.debug("CustomMessage_SignUp" + link);
            event.response.emailSubject = "Samplifier email verification";
            event.response.emailMessage = buildConfirmationEmail(
                indicinaLogo,
                samplifierLogo,
                escapedFirstName,
                link,
                tosLink,
                privacyPolLink
            );
            appMetadata["emailType"] = "SignUp"
        } else if (event.triggerSource === "CustomMessage_ForgotPassword") {
            link = `${baseUrl}/change-password?code=${codeParameter}&username=${userName}&clientId=${clientId}&region=${region}&email=${email}`;
            event.response.emailSubject =
                "Samplifier password reset email verification";
            event.response.emailMessage = buildPasswordResetEmail(
                indicinaLogo,
                samplifierLogo,
                escapedFirstName,
                link,
                tosLink,
                privacyPolLink
            );
            appMetadata["emailType"] = "ForgotPassword"
        } else if (event.triggerSource === "CustomMessage_ResendCode") {
            link = `${baseUrl}?code=${codeParameter}&username=${userName}&clientId=${clientId}&region=${region}&email=${email}`;
            event.response.emailSubject =
                "Samplifier retry email verification";
            event.response.emailMessage = buildConfirmationEmail(
                indicinaLogo,
                samplifierLogo,
                escapedFirstName,
                link,
                tosLink,
                privacyPolLink
            );
            appMetadata["emailType"] = "ResendCode"
        }
        appMetadata["resultMessage"] = "Success"
        console.log(JSON.stringify({"appMetadata": appMetadata}));
    } catch (e) {
        // @ts-ignore
        console.error("Error stack: ", e.stack);
        // @ts-ignore
        console.error("Error name: ", e.name);
        // @ts-ignore
        console.error("Error message: ", e.message);
        appMetadata["resultMessage"] = "Error"
        console.log(JSON.stringify({"appMetadata": appMetadata}));
    }
    return event;
};

// Company source code markers (PRD 9.2). Edit the names to match the company's repositories.

rule internal_hostname {
  meta: category = "source_code" entity = "INTERNAL_HOST"
  strings: $a = /\b[a-z0-9\-]+\.(corp|internal|intra)\.[a-z0-9\-]+(\.[a-z]{2,})?\b/ nocase
  condition: $a
}

rule company_license_header {
  meta: category = "source_code" entity = "LICENSE_HEADER"
  strings:
    $a = /Copyright \(c\) \d{4}[ -]*(\d{4})? *Aegean Meridian/ nocase
    $b = "Proprietary and confidential" nocase
  condition: any of them
}

rule company_package_names {
  meta: category = "source_code" entity = "COMPANY_PACKAGE"
  strings:
    $a = /\bcom\.aegeanmeridian(\.[a-z_]+)+/
    $b = /from aegean_meridian[\w.]* import/
    $c = /@aegean-meridian\/[a-z\-]+/
  condition: any of them
}

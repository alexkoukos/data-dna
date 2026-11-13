// Secrets and credentials (PRD 9.2). `category` tells the policy engine which action applies.

rule pem_private_key {
  meta: category = "secret" entity = "PRIVATE_KEY"
  strings: $a = /-----BEGIN [A-Z ]{0,20}PRIVATE KEY-----/
  condition: $a
}

rule aws_secret_access_key {
  meta: category = "secret" entity = "AWS_SECRET"
  strings:
    $k = /aws_secret_access_key\s*[=:]\s*["']?[A-Za-z0-9\/+=]{40}["']?/ nocase
  condition: $k
}

rule gcp_service_account {
  meta: category = "secret" entity = "GCP_SERVICE_ACCOUNT"
  strings:
    $t = "\"type\": \"service_account\""
    $k = "\"private_key\""
  condition: all of them
}

rule azure_storage_connection {
  meta: category = "secret" entity = "AZURE_CONNECTION"
  strings: $a = /AccountKey=[A-Za-z0-9+\/=]{40,}/
  condition: $a
}

rule database_connection_string {
  meta: category = "secret" entity = "DB_CONNECTION"
  strings:
    $a = /(postgres(ql)?|mysql|mongodb(\+srv)?|redis|amqp):\/\/[^\s:@\/]+:[^\s@\/]+@[^\s\/]+/
  condition: $a
}

rule password_assignment {
  meta: category = "secret" entity = "PASSWORD"
  strings:
    $a = /(password|passwd|pwd|secret|api[_-]?key|token)\s*[=:]\s*["'][^"'\s]{8,}["']/ nocase
  condition: $a
}

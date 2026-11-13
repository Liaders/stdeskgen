pub(crate) fn is_transport_error(error: &str) -> bool {
    let error = error.to_ascii_lowercase();
    if ["password", "permission", "denied", "authentication", "rejected", "offline", "not exist", "blocked", "not allowed"]
        .iter().any(|word| error.contains(*word)) {
        return false;
    }
    error.contains("reset by the peer")
        || error.contains("connection reset")
        || error.contains("timed out")
        || error == "timeout"
}

#[cfg(test)]
mod tests {
    use super::is_transport_error;

    #[test]
    fn offers_retry_for_reset_without_os_error_code_and_timeouts() {
        for error in ["Reset by the peer", "Connection reset by peer (os error 104)",
                      "Connection timed out", "Timeout"] {
            assert!(is_transport_error(error), "{error}");
        }
    }

    #[test]
    fn does_not_offer_retry_for_authentication_or_availability_errors() {
        for error in ["Wrong Password", "Permission denied", "Offline", "ID does not exist", "Authentication timed out"] {
            assert!(!is_transport_error(error), "{error}");
        }
    }
}

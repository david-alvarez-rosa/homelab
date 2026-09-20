require ["fileinto", "mailbox"];
if header :contains "Subject" "Report Domain:" {
  fileinto :create "Archive";
  stop;
}
if header :contains "X-Spam" "Yes" {
  fileinto :create "Junk";
  stop;
}

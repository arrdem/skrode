# BBDB
The Big Brother Database; a CRM for the rest of us.

This project is inspired by and named after [Emacs BBDB](https://www.emacswiki.org/emacs/BbdbMode),
a tool for building and maintaining a contacts list by automatically analyzing various sources such
as email and IRC.

I never got BBDB to work for me for a number of reasons...

- I simply don't run long-lived Emacs instances (for long-lived meaning n > 12h)
- BBDB doesn't support Twitter
- I don't use Emacs as my mail client

The goal of this project is to develop a multi-worker queue architecture capable of processing many
source streams from services such as Twitter, IRC, Slack and soforth as well as traditional BBDB
sources such as Atom feeds and email.

## License

Copyright Reid 'arrdem' McKenzie. All rights reserved. Commercial deployment is expressly forbidden.

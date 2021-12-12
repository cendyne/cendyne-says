# cendyne-says

Two telegram bots, saying something and yelling something.

Saying something has a few variants: A speech bubble, smol, and breathes.
Within saying smol it will show a single character with a simple shake, violent shake, or a wiggle.
Within breathes, it will spew as many copies as a thing it can within the 64kb limit.
The speed bubble variant has its own dynamic word wrapping and scaling.

Yelling actually has a local sqlite database and can remember results.

# Dependencies

There's not really a python package file or whatever, you'll have to look at the sources and try to run it.

Also, you'll have to patch the python lottie dependency, search for font.cmap and replace it with font.font.cmap. The fix is not published yet.

```
pip install -r requirements.txt
```
On freebsd, py38-sqlite is needed too

In the vscode container, it may be stupidly slow in the terminal because of git.
`git config codespaces-theme.hide-status 1` will hide the status.

# Environment
Copy the `example-dot-env` file to `.env` and set things up.

* `ADMIN` is your user id
* `REVIEW_CHAN` is the numerical id (likely negative in value) for a channel where submitted stickers are reviewed
* `LOG_CHAN` is the numerical id (likely negative in value) for a channel where stickers are logged.
   It is a necessary evil, inline results can only show previously sent stickers.
* `NO_RESULTS` is for yell bot, it is the file ID for a sticker that represents no results. See the logs for the file id.
* `YELL_TUTORIAL` is an intro video of how to use the bot, it is the file ID for an mp4 animation. 

Note that file ids are only valid within the same bot, all obtained file IDs must be from you submitting content to the bot, or the bot creating the content.

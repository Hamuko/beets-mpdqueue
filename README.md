# beets-mpdqueue

## Description

beets-mpdqueue is a [Beets](http://beets.io/) plugin to add files imported to the Beets library to [Music Player Daemon](https://www.musicpd.org/) queue, so you can start playing your new music immediately.

## Usage

To use the plugin, enable it in the Beets configuration by loading the `mpdqueue` plugin (see [Using Plugins](https://beets.readthedocs.io/en/latest/plugins/index.html#using-plugins) in the Beets documentation). After you have done this, your newly imported files are always added to the end of the MPD queue automatically.

One important thing to note is that this plugin does not do anything when you reimport Beets library items.

### Configuration

The only configuration for this plugin are the MPD server address, port and password, which are configured the same way as with the [MPDUpdate](https://beets.readthedocs.io/en/latest/plugins/mpdupdate.html) plugin included with Beets.

    mpd:
        host: localhost
        port: 6600
        password: seekrit

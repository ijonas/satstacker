# satstacker

Python script to automate the daily purchase of Bitcoin using the Kraken exchange. Typically run from a Raspberry Pi using a cron job.

![My Satstacker: Tinipy](https://github.com/ijonas/satstacker/blob/main/images/satstacker.jpg?raw=true)

# Introduction

The Bitcoin community is full of advice around dollar-cost-averaging (DCA) and "stacking sats". So I wrote this script to help me (and you) DCA daily.
I run it on a tiny $10 [Raspberry Pi Zero W](https://www.raspberrypi.org/products/raspberry-pi-zero-w/) computer. Every day the Pi Zero executes the script at 5am and by the time I wake up at 6am I've got a few more sats than the day before. *A nice way to start the day.*

Every month on payday I wire some fiat funds across to Kraken and leave them as fiat sitting in my Kraken account. Throughout the month the script
connects and takes a chunk of fiat money and places a *limit order* using the last bid price on the Kraken exchange.

The script places limit orders rather than market orders to minimise the [transaction costs](https://www.kraken.com/en-gb/features/fee-schedule) from the exchange. This sometimes means that your order can take a while to fill if BTC is rocketing up. From experience though Kraken usually fills the order in under an hour.

Now we all love that BTC is in a bull run. However this poses a little problem for this script depending on your monthly budget. The minimum purchase volume
for BTC on Kraken is [0.0002 BTC](https://support.kraken.com/hc/en-us/articles/205893708-Minimum-order-size-volume-for-trading). So if the current price of BTC is $40,000 (oh how I miss those days) then you'd need to spend $8 per day to buy 0.0002 BTC. You would need a monthly budget of 30 days * $8 = $240.

If the price rises to $80,000 then your budget needs to be $480 per month, or you switch from a daily purchase to buying BTC every 2 days to stay within that $240 budget. Now luckily with v1.1 of this script I've added an auto-balancing ability. If you've got enough fiat balance in your account to buy the minimum value or more for the 30 days of the month then the script will buy daily. For example if you've got $6000 to spend each month, then the script will buy $6000 / 30 days = $200 worth of Bitcoin every day. 

If you don't have funds for the minimum amount every day then the script will figure when you can next afford to buy given today's price. So if the BTC price is $90,000 🚀 and you have a budget of $180 / month, then the script will buy 0.0002 BTC every 3 days.

# Installation on a Raspberry Pi

This script can run from anywhere there's a *NIX environment (MacOS, cloud-based Linux, or WSL). It'll probably run on Windows too. However, finding a good use for a Raspberry Pi you have lying around the house increases your Geek-kudos tremendously.

So I'm assuming you've [got a Raspberry Pi ready](https://github.com/ijonas/satstacker#getting-a-raspberry-pi-ready), installed with a recent Raspberry Pi OS. You've got access to the command-line and your Pi has an internet connection (wifi or wired doesn't matter).

Install git

    sudo apt-get install git 

Clone the repository

    cd
    git clone https://github.com/ijonas/satstacker.git
    cd satstacker
    pip3 install -U python-dotenv requests
    cp sample.env .env

For the next step you need Kraken API keys so that the invest.py script can place orders on your behalf. To get a pair of keys [follow these instructions](https://support.kraken.com/hc/en-us/articles/360000919966-How-to-generate-an-API-key-pair-) 

Edit your .env file to add your Kraken API keys and trading pair information

    API_KEY=...
    API_SECRET=...

    # FOR BTC
    MINIMUM_BUY_VOLUME=0.0002

    TRANSACTION_LOG=/home/pi/satstacker/satstacker-transactions.csv

    # Common BTC Pair Name  - Kraken BTC Pair Name
    # BTCDAI                - XBTDAI
    # BTCGBP                - XXBTZGBP
    # BTCUSD                - XXBTZUSD
    # BTCEUR                - XXBTZEUR
    TOKEN_PAIR=XXBTZGBP
    CURRENCY=ZGBP

    LIVE_PURCHASE_MODE=false

The token pair above shows I'm buying BTC using GBP - XXBTZGBP is the identifier Kraken uses for BTCGBP. Each time the script is called it places an order for £25.

Please make sure MINIMUM_BUY_VOLUME is up to date as Kraken lowered the threshold at the start of 2021.
Make sure TRANSACTION_LOG file path is accurate. The script now records the transactions in a history CSV file which it also uses to determine when to next buy.
Adjust your TOKEN_PAIR and CURRENCY to suit your token pairing that you're using to stack sats.

At this point you should be able to execute the script 

    python3 invest.py

It will either print a "success" message or complain that you have insufficient funds in your Kraken account.

To switch the script into "live spend money mode" set the environment variable LIVE_PURCHASE_MODE in your .env file to `true`.

# Running the script every couple of days

The great thing with running it on a Raspberry Pi is its usually switched on all the time, draws little power, and comes with a built-in scheduler: cron.

Check where your python3 interpreter is installed:

    which python3         

My Pi says:

    /usr/bin/python3

Run the following commands to setup a schedule that runs the script every 3 days at 5am:

    echo "0 5 * * * /usr/bin/python3 /home/pi/satstacker/invest.py >/dev/null 2>&1" | crontab -

In the line above the first digit-'0' refers to 0-minutes past the hour, the first digit-`5` refers to 5am. To learn more about cron schedules play around with [crontab-generator](https://crontab-generator.org/).

Confirm that the line has been added to the cron schedule:

    crontab -l

*That's It. Untold riches lie ahead*

# Script support for other tokens like ETH, etc.

You can use the same script to buy ETH etc. by changing the token pair in the .env file.  You'd also need to change the `minimum_vol` constant near the top of the script to reflect the [minimum volume for ETH](https://support.kraken.com/hc/en-us/articles/205893708-Minimum-order-size-volume-for-trading) or whatever. The log message saying you've "stacked sats" would be a confusing 😁.

# Script support for other exchanges

At the moment this script only supports Kraken as the exchange to buy BTC from. AFAIK, all exchanges have good APIs. However I like Kraken because of their excellent customer service and fiat on/off-ramps.

For a free Kraken account [join here](https://kraken.com). 

# Future plans

This script is pretty basic, but I've got plans to enhance it over time (read: weekends).

1. Telegram notifications
2. More sat-stacking by automatically transfering your BTC to Block.Fi and earning interest there.

My intention is for the list above to be optional so you can still run the script in "basic" mode.

# A note for UK-based users of this script.

To minimise bank transfer fees I recommend setting up a monthly standing order to Kraken. To find the details log on to Kraken and 

1. Click *Funding* Tab
2. Click *Deposit GBP*
3. From the *Deposit Method* choose `Clear Junction (FPS/BACS)`.
4. Note down the *Account Name*, *Sort Code*, *Account Number* and most importantly *Reference* details 

The *Reference* is your personal reference ID to ensure that the monies from your bank account end up in your Kraken account (and not mine 😁). The *Reference* doesn't change so use it when setting up your standing order.

# Contributing

Feel free to open a PR if I've missed something or you've got something cool to add.

# Support for non-techies

I appreciate the installation instructions might still be daunting for a layperson to follow. Feel free to [open up an issue](https://github.com/ijonas/satstacker/issues) and ask questions.

I'm also thinking of doing some Youtube videos to help newbies build a Raspberry Pi with Satstacker installed.

My email is always open too: [ijonas@ijonas.com](mailto:ijonas@ijonas.com). I'd love to hear your feedback, comments or questions.

My twitter is: [@ijonas](https://twitter.com/ijonas).

# Crypto Scams

Please be warned: I will never ask you for your BTC private keys or seed phrase. I will never ask for your API keys. Anyone that does is a scammer. 

Don't share your Satstacker `.env` file with anyone either (particularly when asking for help/support), it contains your Kraken API keys.

# Thanks

A special thanks goes out to Alexander Leishman [who's blog post](https://www.alexleishman.com/posts/hmac-in-ruby) showed me how to do all the message-signing-magic.

# Getting a Raspberry Pi ready

Getting setup with a Raspberry Pi Zero W isn't difficult. You don't need any programming skills, but you will need to use a text editor and enter some basic commands at the command line.

Materials you need:
* [Raspberry Pi Zero W](https://shop.pimoroni.com/products/raspberry-pi-zero-w)
* [16Gb Flash Card](https://shop.pimoroni.com/products/16gb-class-10-microsd-card)
* [Pi Zero Case](https://shop.pimoroni.com/products/official-raspberry-pi-zero-case)
* [Micro USB Power Supply](https://shop.pimoroni.com/products/raspberry-pi-universal-power-supply) - or use one from an old cellphone.

Download the [Raspberry Pi OS Lite - Operating System](https://www.raspberrypi.org/software/operating-systems/#raspberry-pi-os-32-bit).

Now follow the excellent guide in [this Youtube video](https://www.youtube.com/watch?v=3VO4vGlQ1pg&ab_channel=Refactored).

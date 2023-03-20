# Malicious Software Packages


<p align="center">
  <img src="./image.png" height="350" />
</p>

This repository is an open-source dataset of malicious software packages identified by Datadog, as part of our security research efforts in software supply-chain security. Most of the malicious 
packages have been identified by [GuardDog](https://github.com/DataDog/guarddog).

Current ecosystems:
- PyPI

## Usage

Malicious samples are available under the **[samples/](samples/)** folder and compressed as an encrypted ZIP file with the password `infected`. The date indicated as part of the file name is the 
discovery date, not necessarily the package publication date.

You can use the script [extract.sh](./samples/pypi/extract.sh) to automatically extract all the samples to perform local analysis on them. Alternatively, you can extract a single sample using:

```
$ unzip -o -P infected samples/pypi/2023-03-20-pydefender-v1.0.0.zip -d /tmp/
Archive:  samples/pypi/2023-03-20-pydefender-v1.0.0.zip
   creating: /tmp/2023-03-20-pydefender-v1.0.0/
```

## License

This dataset is released under the Apache-2.0 license. You're welcome to use it with attribution.


You can cite it in a paper using:

```
@misc{AITextClassifier, 
    month     = Mar,
    day       = 20,
    journal   = {Open-source Dataset of Malicious Software Packages},
    publisher = {Datadog Security Labs},
    url       = https://github.com/datadog/malicious-software-packages, 
    date      = 2023,
}
```

## Disclaimer

* This repository contains actively malicious software that was published by threat actors. Do not run it on your machine.
* This dataset may suffer from selection biais, as it was mostly identified. As such, it may not accurately represent the landscape of software supply-chain security malware.

## Contributions

At the time, the repository is not accepting contributions. However, if you'd like to share an interesting finding with us, reach out at securitylabs@datadoghq.com!
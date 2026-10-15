All 24 packet hashes match. All packets admit a defensible relation under the supplied definitions. Four cases require `unresolved` because their referents affect the relation; those component uncertainties are recorded explicitly.

```json
{
  "cases": [
    {
      "packet": "p01.json",
      "packet_sha256": "d65f82e590a5b15394c23401c7faae6d9d2acdaf6c67a6e84c8106a0a9fc0a07",
      "relation": "unresolved",
      "admissible": true,
      "components": {
        "interpretability": "blocked",
        "relevant_conflict": "no",
        "incompatible_fact": "unanswerable",
        "complete_warrant": "unanswerable"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "The page headings for the 09:00 focusing run and the 20:00 closing show both read 'Screening'."
        },
        {
          "source": "source-2",
          "quote": "The title-reel image was visible on the screen during that run."
        },
        {
          "source": "source-2",
          "quote": "The 20:00 closing-show entry is unchanged: the screen remained dark throughout its title reel."
        }
      ],
      "rationale": "The draft does not identify which screening it means. The corrected focusing-run account supports image appearance, whereas the closing-show account contradicts it. The correction resolves the earlier focusing-run statement; these are different events, not conflicting independent accounts.",
      "uncertainties": [
        "Incompatible fact and complete warrant depend on the unidentified screening and cannot be fixed independently."
      ]
    },
    {
      "packet": "p02.json",
      "packet_sha256": "352c2cdcc9eb4ad79aa5dd57fb0c7a00da88ce08ba32f4c2c1eb770cbd1c13b9",
      "relation": "unresolved",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "yes",
        "incompatible_fact": "yes",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "As the canvas cover was lifted, I saw a blue border around the central bird."
        },
        {
          "source": "source-2",
          "quote": "At the moment its canvas cover was lifted, the border around the central bird was amber, not blue."
        }
      ],
      "rationale": "Two independent eyewitness accounts give incompatible colors for the same border at the same unveiling. Neither is corrected or otherwise resolved.",
      "uncertainties": []
    },
    {
      "packet": "p03.json",
      "packet_sha256": "ebdfbaf028f368aa605d3503e4ddad24d85e9ffe5c4e9e57172fffb07d84fd16",
      "relation": "unsupported_extension",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "The image-observation field is blank; there is no booth or house observation of the projected image for this show in the ledger."
        },
        {
          "source": "source-2",
          "quote": "I have no image observation to add for the 14:00 matinee."
        }
      ],
      "rationale": "The sources supply no image observation for the paid matinee. A running-order entry does not establish projected image appearance, and the absent observation does not establish darkness.",
      "uncertainties": []
    },
    {
      "packet": "p04.json",
      "packet_sha256": "19c0a39051d9c16df65f4a1a7c61745362ec1ebe72597fe422aa37948664cc94",
      "relation": "contradicted",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "yes",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "The cover was carried away before the speeches."
        },
        {
          "source": "source-2",
          "quote": "The cover was carried away before the speeches."
        }
      ],
      "rationale": "Both accounts explicitly describe removal of the cover during the opening. Their disagreement about border color does not concern whether the cover stayed on.",
      "uncertainties": []
    },
    {
      "packet": "p05.json",
      "packet_sha256": "d4eb0647d472aabe7feaa4d389123a0b177c1b66d9589cc9704bb6f800b1579d",
      "relation": "supported",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "yes"
      },
      "evidence": [
        {
          "source": "source-2",
          "quote": "The title-reel image was visible on the screen during that run. I checked my photograph of the screen, which includes the 09:00 focusing slate. I retract the sentence saying that the screen remained black during the 09:00 title reel."
        }
      ],
      "rationale": "The observer explicitly corrects and retracts the earlier darkness statement for the identified focusing run, supplying a checked photographic basis for image appearance.",
      "uncertainties": []
    },
    {
      "packet": "p06.json",
      "packet_sha256": "5b595b7efc0bcd2e9afa1d0c45091ca51f2dd33476f1c8e303acf5c069e96f63",
      "relation": "contradicted",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "yes",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-2",
          "quote": "First-time singers rehearsed the same Catalan verse in the loft before moving to the side hall. In each room they omitted the final consonants that the coach had asked them to pronounce. The coach marked their pronunciation incorrect in both rooms."
        }
      ],
      "rationale": "The beginner-session account explicitly reports incorrect pronunciation in the loft. Correct renditions by returning members concern a separate group and session.",
      "uncertainties": []
    },
    {
      "packet": "p07.json",
      "packet_sha256": "aa0c8c78a9242bf55aadb4ba8ee85414a30e784af2d4d034cc95fc190c6c23fc",
      "relation": "contradicted",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "yes",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "20:00, closing show: The house observer watched the screen throughout the title reel. It remained dark throughout that reel."
        },
        {
          "source": "source-2",
          "quote": "The 20:00 closing-show entry is unchanged: the screen remained dark throughout its title reel."
        }
      ],
      "rationale": "The sources explicitly retain complete darkness during the closing show's title reel. The focusing-run correction does not apply to this show.",
      "uncertainties": []
    },
    {
      "packet": "p08.json",
      "packet_sha256": "19d4ed89ed5dc52b708a62ceb3663afa1949d2a23c7671af13a280a3a93e4395",
      "relation": "contradicted",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "yes",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "In the daylight inspection, Kesta's glaze was cobalt blue and glossy. Tavi's glaze was ochre and glossy."
        }
      ],
      "rationale": "The notebook explicitly gives Tavi's glaze an incompatible color at the stated inspection. The independent disagreement about Lumo's rim is irrelevant.",
      "uncertainties": []
    },
    {
      "packet": "p09.json",
      "packet_sha256": "8f16614bad9dd54ee960de7ef9add0abf7658412b10a2fe980749c0af4da4b0b",
      "relation": "unsupported_extension",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "At the end, Léa said, 'It feels quicker to get going.'"
        },
        {
          "source": "source-1",
          "quote": "Nobody timed scarf weaving or recorded scarf-completion durations during the session."
        },
        {
          "source": "source-2",
          "quote": "The delivery timing concerns the trolley journey. The scarf-weaving session was a separate task in the weaving room."
        }
      ],
      "rationale": "Bobbins were used, but the subjective impression and unrelated delivery timings do not establish shorter scarf-weaving time. Absence of weaving measurements does not establish that weaving failed to become faster.",
      "uncertainties": []
    },
    {
      "packet": "p10.json",
      "packet_sha256": "04975f45f086f1c7db614f325a8d76f52c6e439bb8295244a4d5fbeb948c2a71",
      "relation": "unsupported_extension",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "These entries record surface color and appearance; the notebook contains no washing observations."
        },
        {
          "source": "source-2",
          "quote": "Production note: The Kesta wording was assembled only from the 9 September notebook's color and gloss entry. No washing report was used for the caption."
        }
      ],
      "rationale": "The dishwasher-proof statement is derivative of color and gloss observations, which supply no washing warrant. Nothing states that the glaze is not dishwasher-proof.",
      "uncertainties": []
    },
    {
      "packet": "p11.json",
      "packet_sha256": "a60c25dc3b59748c120d48eb1f98170c51166dcc5b534c582a6366130bc5ff1a",
      "relation": "unsupported_extension",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "This register covers the workshops; the courtyard program lists repertoire and seating."
        },
        {
          "source": "source-2",
          "quote": "Audience members arrived for the evening courtyard performance."
        }
      ],
      "rationale": "The sources record audience arrival and a program, without an audience rendition or pronunciation assessment. The workshop results concern other groups and locations.",
      "uncertainties": []
    },
    {
      "packet": "p12.json",
      "packet_sha256": "021b07dd184b479983af1afe8d73eb6c359ff5966833a0cba9bdc172c869380f",
      "relation": "unresolved",
      "admissible": true,
      "components": {
        "interpretability": "blocked",
        "relevant_conflict": "no",
        "incompatible_fact": "unanswerable",
        "complete_warrant": "unanswerable"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "The order book calls each tree 'new pear'."
        },
        {
          "source": "source-2",
          "quote": "C, beside the cistern: open blossoms on the branches; white cloth tie intact."
        },
        {
          "source": "source-2",
          "quote": "S, beside the tool shed: no flowers on the branches; white cloth tie intact."
        }
      ],
      "rationale": "The draft does not distinguish the two trees called new pear. The survey supports flowering for one and contradicts it for the other, without a factual conflict between accounts.",
      "uncertainties": [
        "Incompatible fact and complete warrant depend on which tree the assertion designates."
      ]
    },
    {
      "packet": "p13.json",
      "packet_sha256": "34f1556500fea65d10a47ab6883fc319c2b0d931ba1f21efce05eeb167a03e87",
      "relation": "supported",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "yes"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "The weavers installed prewound bobbins and used them for the scarf-weaving session."
        }
      ],
      "rationale": "The dated log directly establishes bobbin use for scarf weaving. The assertion claims no improvement in duration.",
      "uncertainties": []
    },
    {
      "packet": "p14.json",
      "packet_sha256": "12f1d5688dc60af0199b3210b731a1622a45d11141c02183eef5798a24d6e978",
      "relation": "contradicted",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "yes",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-2",
          "quote": "S, beside the tool shed: no flowers on the branches; white cloth tie intact."
        }
      ],
      "rationale": "The dated survey explicitly records no flowers on the identified shed tree.",
      "uncertainties": []
    },
    {
      "packet": "p15.json",
      "packet_sha256": "d001a4f34d4d16ca5a34ce8e1bf1ec589902f23481facb3cd0e7238dbab8249c",
      "relation": "supported",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "yes"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "I made this note from what I saw at the unveiling."
        },
        {
          "source": "source-2",
          "quote": "This is my own recollection of watching the unveiling."
        }
      ],
      "rationale": "Both supplied accounts describe personal observation of the identified unveiling. Their disagreement about color does not prevent establishing that two eyewitness accounts describe it.",
      "uncertainties": []
    },
    {
      "packet": "p16.json",
      "packet_sha256": "543afb287740c7ad4441d1c298fbaa3583bc87806ec377f76ed714a2a5f301f4",
      "relation": "unsupported_extension",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "As the canvas cover was lifted, I saw a blue border around the central bird."
        },
        {
          "source": "source-2",
          "quote": "At the moment its canvas cover was lifted, the border around the central bird was amber, not blue."
        }
      ],
      "rationale": "Neither account establishes border materials or recycled provenance. Their disagreement about color neither establishes nor contradicts recycled-glass construction.",
      "uncertainties": []
    },
    {
      "packet": "p17.json",
      "packet_sha256": "a900768eeb65065921ba3d75c531bd0249a835839e5da505582e04147934525a",
      "relation": "supported",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "yes"
      },
      "evidence": [
        {
          "source": "source-2",
          "quote": "C, beside the cistern: open blossoms on the branches; white cloth tie intact."
        }
      ],
      "rationale": "The dated survey directly records blossoms on the identified cistern tree.",
      "uncertainties": []
    },
    {
      "packet": "p18.json",
      "packet_sha256": "028a0fad0260798547fa702fcde7a9dff6d7b6e01516e0182045aa4fe1633e25",
      "relation": "unresolved",
      "admissible": true,
      "components": {
        "interpretability": "blocked",
        "relevant_conflict": "no",
        "incompatible_fact": "unanswerable",
        "complete_warrant": "unanswerable"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "The pronunciation coach listened to their rendition in each room and marked both renditions correct."
        },
        {
          "source": "source-2",
          "quote": "The coach marked their pronunciation incorrect in both rooms."
        },
        {
          "source": "source-2",
          "quote": "The returning choir members and the first-time singers had separate workshop sessions."
        }
      ],
      "rationale": "Both groups rehearsed in the loft, and the draft does not identify its group. One group's rendition was correct and the other's incorrect. These distinct sessions do not constitute conflicting accounts of one rendition.",
      "uncertainties": [
        "Incompatible fact and complete warrant depend on the unidentified group."
      ]
    },
    {
      "packet": "p19.json",
      "packet_sha256": "d565cded79f4d5a7647d46cceb6fb570ecad3be573461d782561e87df97d70a1",
      "relation": "supported",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "yes"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "In the daylight inspection, Kesta's glaze was cobalt blue and glossy."
        }
      ],
      "rationale": "The notebook directly establishes Kesta's color at the stated inspection. The Lumo-rim disagreement concerns a different fact.",
      "uncertainties": []
    },
    {
      "packet": "p20.json",
      "packet_sha256": "ae1a8f704d26a078bbaf70b1d4802550951990e4beafed59ad087b5b3c4e4e24",
      "relation": "unsupported_extension",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-2",
          "quote": "This survey records the trees on 19 April. It contains no later visits."
        }
      ],
      "rationale": "The April blossom observation does not establish ripe fruit on the September date. The sources contain no incompatible September observation.",
      "uncertainties": []
    },
    {
      "packet": "p21.json",
      "packet_sha256": "31c95aa55a9c9948505ee3e3c9e91c6290a0d4786ddc678cad3a1c574562fb4c",
      "relation": "unresolved",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "yes",
        "incompatible_fact": "yes",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "At the 17:00 handover-bench inspection, before the Lumo bowl was wrapped, I examined its rim. The rim was continuous and had no crack."
        },
        {
          "source": "source-2",
          "quote": "I also attended the Lumo bowl's 17:00 handover-bench inspection on 9 September, before wrapping. I examined its rim during that inspection and saw a hairline crack through the rim."
        }
      ],
      "rationale": "Two independent observations describe incompatible rim conditions at the same inspection. The bulletin's derivative qualification applies to Kesta wording, not its author's personal Lumo observation. No supplied correction resolves the disagreement.",
      "uncertainties": []
    },
    {
      "packet": "p22.json",
      "packet_sha256": "8abe1f09ea20336f1cddfb5fbf93f80ee1ac9281c0411af776ec616cee9e09f9",
      "relation": "contradicted",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "yes",
        "complete_warrant": "no"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "Nobody timed scarf weaving or recorded scarf-completion durations during the session."
        },
        {
          "source": "source-2",
          "quote": "The delivery timing concerns the trolley journey. The scarf-weaving session was a separate task in the weaving room."
        }
      ],
      "rationale": "The log explicitly denies the claimed measurement. Measurements of delivery journeys do not conflict with that denial.",
      "uncertainties": []
    },
    {
      "packet": "p23.json",
      "packet_sha256": "f1eb9e2db12ac71567daf5c7bb28f1e8ec835d74023dc771253051717c1166b4",
      "relation": "unresolved",
      "admissible": true,
      "components": {
        "interpretability": "blocked",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "unanswerable"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "Nobody timed scarf weaving or recorded scarf-completion durations during the session."
        },
        {
          "source": "source-2",
          "quote": "The deliveries along the covered passage took less time than those along the courtyard passage."
        },
        {
          "source": "source-2",
          "quote": "The delivery timing concerns the trolley journey. The scarf-weaving session was a separate task in the weaving room."
        }
      ],
      "rationale": "The draft does not identify the change or task. Shorter deliveries are supported, whereas shorter weaving is unestablished. Neither candidate has an explicitly incompatible duration fact, so that component remains no despite the blocked overall relation.",
      "uncertainties": [
        "Complete warrant depends on whether the assertion designates the route change and deliveries or the bobbins and weaving."
      ]
    },
    {
      "packet": "p24.json",
      "packet_sha256": "dda542d7cd2a75f43a147a249218eb5bda1bcc41b10cf8e85f301ce5de956ab2",
      "relation": "supported",
      "admissible": true,
      "components": {
        "interpretability": "clear",
        "relevant_conflict": "no",
        "incompatible_fact": "no",
        "complete_warrant": "yes"
      },
      "evidence": [
        {
          "source": "source-1",
          "quote": "Returning choir members rehearsed the Catalan verse in the loft and then in the side hall. The pronunciation coach listened to their rendition in each room and marked both renditions correct. Each room appears as 'small room' on its booking sheet."
        }
      ],
      "rationale": "Both possible small-room referents have a correct rendition by the identified returning members. The room ambiguity leaves the relation unchanged, and beginner results concern a different group.",
      "uncertainties": []
    }
  ]
}
```

DONE
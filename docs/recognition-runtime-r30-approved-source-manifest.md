# R30 approved source manifest for Git delivery

This records existing R28/R30 artifact hashes; it creates no authority or policy.
The approved ZIP and JSON manifest remain unchanged and are retained through the
artifact handoff, not committed from local staging.

- ZIP SHA256: d1eb8ddc0dddae3dc1e4cbd26221dc0b859ba6ca3a141b69e079ddeaa3391e59.
- Original JSON manifest SHA256: 1ff86e5711893df4d54e4610496c12ee98697440e50fe96d23c9ddac64f713fd.
- Source evidence: [R28](recognition-runtime-security-production-integration-4e-20-R28.md).
- Authorization: [R30](recognition-runtime-security-production-authorization-decision-4e-20-R30.md), deployment only.

Repository .gitattributes preserves these exact source bytes in Git. When staging
a future authorized commit, include the complete manifest source set and use
explicit path-scoped renormalization for tracked files so existing Git LF blobs
are not silently retained where the approved source bytes are CRLF. This is Git
transport metadata, not a source rewrite. Verify staged/checkout bytes against
this record before deployment. No global Git setting is changed.

## Production package source

| Path | SHA256 |
| --- | --- |
| src/review/recognition/__init__.py | 91b9b8b18a00831aa954ca73d6152fc1f311c6552df25e93fc27b13c2fc198a6 |
| src/review/recognition/achievements.py | d5b9b9c6a2830434581166c0a06b4ee4b0040a977325cfa1a878448b7f7f023a |
| src/review/recognition/activation.py | fc2d84ec553af3cd5a93fabe0be22cc1deda053dd5796f1c0c05f16868128645 |
| src/review/recognition/activation_schema.py | 4d7a6617abe504f5dbbf06df26dcf2100d9d78ac16eddeec562df1899f20a59d |
| src/review/recognition/admin_auth.py | 8c670810f7ba6e81a6b3287d1b8a8bc19fa46319e849ed05404fa82e52db9089 |
| src/review/recognition/admin_routes.py | 4987f998f486da7c52b72e4d65f81d5890b6ee69bf82c563c58fd00aa2a82952 |
| src/review/recognition/administration.py | 42dedf309a74adf555b514d6dcf47a749aa1a9452800e9b54cac074836e28c45 |
| src/review/recognition/administration_schema.py | 738591181c5f51e201fa07a932c77df140241f8435f8adb30ced8ed82d26430c |
| src/review/recognition/approval_schema.py | f76b5d2e2a329407d9a4a8327f395c8846313a60fe3e1144251c9e87a485ad85 |
| src/review/recognition/approvals.py | 153b47e810b03d814183f6d68527610cea611a677a7a7c883dc2e3d9194e1805 |
| src/review/recognition/artifacts.py | 7e59c307a12f79097a37bad1304f326ddc0b9b46a22c0282a7b68d46da55db30 |
| src/review/recognition/authority.py | f620e47a9254c0889e473b0a7a6befca71c5b56a0806a93688dcaad109a71b0e |
| src/review/recognition/authorization.py | d70ba37634e0dcb149cf178fbf39c9cf7d5479c79a3fcf8517f015cda51f074c |
| src/review/recognition/backfill.py | 8288b0bf7795931b2e3d5333b8c27c569e53fa667a334d6766adda06d1639f7d |
| src/review/recognition/cross_dimension.py | 1f2d2d984e14a229e2b1eb3b53f7026f229f2a20d8e6871a5cae67b6963ac3ae |
| src/review/recognition/dependencies.py | d26bc0ddde1a6df329475fa5e1d0d2126b3f1518b094bb53b791160e142d790f |
| src/review/recognition/enrollment.py | fe443653ba3b1efc3fb3d0f93a5c65421fe16f993f704acf951ead85d2c9fd50 |
| src/review/recognition/event_schema.py | 7c85c4d04ef183711bac01fcf9811ed1860096250d9e6b960a7503f4ddf80a83 |
| src/review/recognition/events.py | 49cb26017ea6e02dc44901aefa67eb245ff37df126cfdff89b5c78e51435a0c5 |
| src/review/recognition/execution.py | b276ac88b1f970fb4ae25964f930c7068cdaf4fb5e984c4ac2a4423d81cfec77 |
| src/review/recognition/execution_schema.py | 94fa62893f663432ddd5ebc3eda5a6bf6733a00783fa778509f9cd7427af9a66 |
| src/review/recognition/first_look_launch.py | 995b19156879e561cf75b6b83281f89cadcfe9a1216fe5b4710f52f171385ba3 |
| src/review/recognition/first_looks.py | 3426031aec8c2522f069ae26342e4b2b2ea7ac18c7f945a8c3ff9b94941a34fe |
| src/review/recognition/geography.py | 430468e8a0eab393ee506c03b150ba5def5bf96a25b8b7cc89eca49246b9e2af |
| src/review/recognition/integrity.py | 8a6e779d3c02f8dfc2fd94362701abcc3d28994317705ada6e235365fe0d914d |
| src/review/recognition/live_first_look_schema.py | e3c0748c74771efe87c522f1d5b9bdb54116d759090bacea3c4e70a112ad26a9 |
| src/review/recognition/live_first_looks.py | cf1f615b9662d3b6c9502f4cc0ab826201a4c643a2f9f3360059ab5e35eed3df |
| src/review/recognition/local_execution.py | 80c88a53750cc159bd2ca38f5d72b6507bde41b595ac82a5b94a8b4e0664ffe7 |
| src/review/recognition/local_readiness.py | 6bd302217cd8389aa634e689d0487b36cab1e78be6a9b6cf809e640d0e6a7cf0 |
| src/review/recognition/operation_schema.py | 1a9f35b840538e36382fe0fb39e6c8426e5d6820746afd7d41d3366bcd0b4db4 |
| src/review/recognition/operations.py | 34dac8a16ba45cd9e71eb7355e467f103f5a3c176d3941086b3cbdb023ea8358 |
| src/review/recognition/permanent.py | 76eb984f68629421fe8b856264cf35f5bc99827a131b7ca7884cdf6a1c8b8ee0 |
| src/review/recognition/permanent_schema.py | 7afade80c17900d7375ed16f3fe94f009f49b2f4fecd4997a4a01210b95d35d0 |
| src/review/recognition/processing.py | 1fe9273bbf874d135b384a76a204fda0f333092f017bb1a5e04f7a67b0e7ee1e |
| src/review/recognition/production_operations.py | 8367cf45a12b0b424dd691897cceea2f92101f3fc325ce05ed430097b44e6739 |
| src/review/recognition/production_receipts.py | 6d437a54eb1158d06d7e5e1f80008bf9693bfb6fdc0c46db3be68b44e2a4ed95 |
| src/review/recognition/qualification.py | d2e9614dff5ae76be9eee100635ca914a77dcc500db333a27da033d25f0dbe9d |
| src/review/recognition/report_connection.py | 9cc64b3778c648ffb2ea0825d6bd18233f55dc450c328f2ed133e893bb75fcd6 |
| src/review/recognition/rules.py | 67e554743593a254cedb33cc0a7a7d79701161a72ee6670e1dd5046963b36450 |
| src/review/recognition/runtime_activated_owner.py | 514cf4f0f988d15b2877fed95975c8c2970c4542d98f5cea2e7ea287cb3ec19b |
| src/review/recognition/runtime_activation_authority_issuance.py | c1fac3564d32fd2e1a10f5fe8132039585a886bbaddb560fb3f83dda43b07fd3 |
| src/review/recognition/runtime_activation_authority_schema.py | f399540df6b27866b1c539b38e21aa3da584bed4c7de43f6e801197de7a52644 |
| src/review/recognition/runtime_admission_validation.py | d3849bb70579fcd3310f3bb00045714870d16c6cf0473e67bd9b7030b4396c75 |
| src/review/recognition/runtime_approval_ceremony.py | dea352b87bdc5a71677b23667b1a3639094d4de09e9b655fe539ced720684608 |
| src/review/recognition/runtime_approval_contract.py | 1cedd6aea4af31a26d5a1b445661638dc43f5a7a9842e800fc9826c94881f454 |
| src/review/recognition/runtime_approval_transaction.py | 55a7bc553db4c7bd7593c4f74fc20e9dca2a2279b11c6c0398a313019433f6e5 |
| src/review/recognition/runtime_approvals.py | c465a30e4f69fc6eec677f8088f003fa8adc5ec3cbf63548cafdad0247404891 |
| src/review/recognition/runtime_attempt_schema_manifest_observation.py | 806fd988d08ea91302104ceebf1eed29de41e49857fb2b32348d6de0a773201d |
| src/review/recognition/runtime_auth.py | 743cbd6eea90c5f27ec6275ea3ee062fb94ed136d4297bd7adb2c0fbc6ecfd65 |
| src/review/recognition/runtime_authority_consent.py | 39ee93eb21d0d19aeee9129abaf74f55680e94da5ff8707c26d795a5c393685d |
| src/review/recognition/runtime_authority_consent_transaction.py | 1d72a6b623f519cd6b2fe810caee3f97b0b58cd1d4cf35478cc8fbc7529efe4a |
| src/review/recognition/runtime_authority_lifetime_policy.py | d6119d7cccb28ecd8e99c6f45c4b0bdac8b44c37d8d2904d132aaa94f4c0e84b |
| src/review/recognition/runtime_challenges.py | 51c7fd3d724339c059c8466ed7925dfd1900b9311b32cd015e1213b6f1419881 |
| src/review/recognition/runtime_claim_consumption.py | 1bc6410f41dcf03a6698c2c04fccc5b5e6809a1b5892808070f891453d98bf35 |
| src/review/recognition/runtime_claim_disposition.py | 73327b5b509cf5289f488d4135bbb1de58edf22f99076ed89e557485934704d6 |
| src/review/recognition/runtime_claim_validation.py | 2f144ee89905b3ce86030dd5ac7cfbe9e2424ec351f67512fc3994e8de67977c |
| src/review/recognition/runtime_decision_outcome_journal_schema.py | c2281dd597388846fe18756d6b288f54fcb49fd92881419c5b208e8ef9f75d83 |
| src/review/recognition/runtime_enrollment.py | 56c105c7b371715b58fa9ceeafd33494399e2adedd0e86138ccae57807ebf316 |
| src/review/recognition/runtime_enrollment_transition.py | 1f363b4a6a21d6ba6f97e5d2a6c74ed530d4586ee9f50c0dbd1435196ba348c0 |
| src/review/recognition/runtime_enrollment_transition_schema.py | fa9760ee9fc5347cc4da0eee8e7f0602531f8c2bf9cb13a79b99871f3c2bfbad |
| src/review/recognition/runtime_evidence.py | abb1616af4ce6f433702d0576127a2553db348c96778a3549391e277dbe89480 |
| src/review/recognition/runtime_execution_admission.py | 5095c7cca75b025aa454413c9288547e8660c4ee0efb5eac2fb490dfd942198e |
| src/review/recognition/runtime_execution_attempt_schema.py | 241baa5694570e242ab9833b6107b0d186facb5297873e2f39c6a70a87b5bbdd |
| src/review/recognition/runtime_execution_claim_schema.py | 37f9cebe1043e10459f7b44b4b2605c271d795e04cb3077a9dc2447811af4b30 |
| src/review/recognition/runtime_execution_claims.py | 9b32ae163309e277eca7a665df25a198be98783607812a5fa69304198e2b7ee7 |
| src/review/recognition/runtime_execution_coordinator.py | 4862d33d75bd20fe868ed4769081ded852e871f36383edb2dd7861d0ebe48f5c |
| src/review/recognition/runtime_finalization.py | 640a3b197befa82824403e7e75b39758ce8f247891c057e48ad7fd747c28fad3 |
| src/review/recognition/runtime_finalization_contract.py | 34c5cd61f6c8b5e9bdf189526b8d8b184bf93a8fae55fbf1d0c73596ce582ed6 |
| src/review/recognition/runtime_finalization_effects.py | 7d70bfb1733a8b88b5c2273cc29acc73f5946565ba4eadb2d5b69ef2af367ad7 |
| src/review/recognition/runtime_finalization_schema_upgrade.py | f26a1fcd5fbf4a896d0c6eacfbea63c9853ab8430c6669a3f88aa1b562e23cc4 |
| src/review/recognition/runtime_finalization_storage.py | 08b289f03d9ea375971d058e30c23e8dfaac6738bc86b1ca623cbd9e47385b45 |
| src/review/recognition/runtime_history_validation.py | 926d0534b1734dccb032e8e31ffeb3b7cc430358d537ab53a516f1b3fa999d62 |
| src/review/recognition/runtime_issuance_schema_inventory.py | e3e7537faee35092c002ef4c8b300ba48fc26851a4feea94143d7f856a73c7c6 |
| src/review/recognition/runtime_operation_contract.py | 6a7ef96b15cb29d75864a864ac948048303c88dbdd0b74dd90277eaed296c748 |
| src/review/recognition/runtime_production_governance.py | 0b7e7b3e002c148e47abbfc595f3525a48cf7635f59932fbbf563d18032ad6e5 |
| src/review/recognition/runtime_profile_schema.py | b5956254fa6e3a9eadab3620fc6cbe69f6fb2d414100c5ed5e893b04e3102429 |
| src/review/recognition/runtime_proposal_records.py | 1b128113b3771c0674a16bc5e8c57d039a2d5b99dd120e25478f46f15b54882b |
| src/review/recognition/runtime_proposal_transaction.py | da93aa9ee2c4421caa1a9467dee58329397a69f57b04751e29c932a12c2147e6 |
| src/review/recognition/runtime_proposals.py | c04f1a06000bbc96781b89a8ba9c71ddbd67c5b6b21353b83e865602f6a8be4d |
| src/review/recognition/runtime_schema_package_lineage.py | 25bce965ace63b127904fe73a223b9567cc507eebb4a8cda9f7f74f26ad49ef4 |
| src/review/recognition/runtime_scope_validation.py | 84c831fe611fec995ed76ccae5d7fc6409e60ed8128ad788f5714c8342d93748 |
| src/review/recognition/runtime_target_entry_owner.py | 1ee39823b2e0f7c03fa98c113df0dbb029e34b8bba8f5957bf979b71a6287026 |
| src/review/recognition/runtime_target_entry_storage.py | 1e329c9ed68226f430e68b43bb869de52e4eb124e105bee33bc364d4f2ea1ae1 |
| src/review/recognition/runtime_validation.py | 55926ec4a031b81653594c86fd83f6109445d5228da725a8627f6911bccffcb4 |
| src/review/recognition/schema.py | cba2dcb85b4a313d0451e4645d9cad324fbeddd2a3024c1ca3896ee635e466a1 |
| src/review/recognition/status.py | b518f471efb91a90a6bc09b28bcb8dc4bc90513c62ef73a7d326a8c4fd2eac00 |
| src/review/recognition/trust.py | d4c98402935d8aa2bb315d3ccc29688730171d6d8a0bcb10bcaed38a60eea1fe |
| src/review/recognition/writer_boundary.py | 56dc688b027639d2d75bab2de57f0e6ae30c9e0f8263a3a32a20f7b0c9c45de8 |

## Existing application dependency references

| Path | SHA256 |
| --- | --- |
| requirements-pilot.txt | 5056444c2594b86a83a301e9811e78de625b312cb5f6daf7e6139387f06ca93d |
| src/amenities/status_synthesis.py | 57eef0e562e4a1aefd8d7f5c93b29e33dc818fa26b6ec94f0f4c7cde75277d6b |

## Approved test evidence source

| Path | SHA256 |
| --- | --- |
| tests/recognition_production_owner_ceremony.py | 4561a2120eb9ddd6db80086e44a8914479fbed2db8aab1910ef30199f46f986d |
| tests/recognition_production_owner_fixture.py | 199ad8d2f1c5fbfdb854cadbe1722b3253a401f9f9891341259271c44db900f2 |
| tests/runtime_owner_fault_probe.py | a3640ceccc2a5d34776b945a179b1311419a6374b0bfcfd1a8ca07726b6de0be |
| tests/test_recognition_runtime_finalization_lifecycle.py | c3914b6588d0f0a7f6c6e2749edf06e0045dfdeb5b72f032bac160c0089f9885 |
| tests/test_recognition_runtime_owner_failures.py | 38afcfe27a1a1a74e89094d504d0c1ca4c8b94618ca21529bf4a27503b56a74e |
| tests/test_recognition_runtime_production_journal.py | 78e427653aa5a4e8efb1ce1c3961393e6cbe502539096d8831249c99e31cdbef |
| tests/test_recognition_runtime_production_owner_lifecycle.py | 596d5311dfedca2ef287c29af658f32f0958296a66f8ebebde3887d5ba9d1462 |
| tests/test_recognition_runtime_production_provisioning.py | d74fbe6759d13019b6265624cc6e9691644667cd032f04441019f98b89b40fbd |

v1 remains 120 seconds and ordinary/default; v2 remains 300 seconds and
prospective/test-only. Nothing here activates or executes recognition.

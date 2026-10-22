# Approved bounded source investigation, no changes
New disassembly from pinned BDSbinary SHA0a490c711d4a2ce075debcd979e8862b7eaba008373f9970f0edbb67f98f9207. No newly generated worlds. Evidence: cityseed4027938806717471239 rawlocate72,-2600 APIcitymember at72,-27,-2600 butbiomeoldgrowthspruce; deepdarkatY-48. Native checks getBiomeAt(g,0,x>>2,-27>>2,z>>2). BDScity vtable0xee8caf0 slot6 0x4e3e390 maps isFeatureChunk by comparison with VillageFeature knownslot6 0x4fbb850. Slot4 getRequiredBiomes,slot5nearest,slot7createStart. Newcityasm passes blockX=chunkX*16,blockZ=chunkZ*16,Y=-27 toBiomeSource vtable+0x38, notrawnavcenter+8. Need identify semantics ofcallee beforeclaimrule.
Bastionseed2706853909057002900 raw1464,1800 netherwastes,variant1468,1784 basalt_deltas, bothmember; seed219044158440418215 raw1640,1672 netherwastes(no memberat3Y),variant1616,1640 basalt_deltas(memberY32,64). Native checks variantcenterquart atY33. Bastionvtable0xee8cb90 slot6isFeatureChunk0x4e3ecf0 calls4fd0b70 then compareshashedbiomenameglobal0xf61f558. Need derive actualargcoordinates andbiomesourcecall notassumebasaltgloballyallowed. Sharedfortresslogic dependsbastion.
Task: tool-free High source analysis ONLYembeddedassembly, derive defensible argumentflow, separate proven fromhypothesis, proposeminimalindependent controls. No scripts/edits/commands/network/BDS/delegates. Do notrepeatpreviousreview speculation asfact. <=700words.

## ancient-city-check.asm
```asm

/Users/lucasraicu/.local/share/antigravity-worker-mcp/predictor-engine-20261020/bedrock_server:	file format elf64-x86-64

Disassembly of section .text:

0000000004008240 <.text>:
 4e3e310:	push	rax
 4e3e311:	mov	rdx, qword ptr [rdi + 0x180]
 4e3e318:	mov	rcx, qword ptr [rdi + 0x188]
 4e3e31f:	mov	rax, rcx
 4e3e322:	sub	rax, rdx
 4e3e325:	cmp	rax, -0x2
 4e3e329:	je	0x4e3e342 <.text+0xe36102>
 4e3e32b:	test	rdx, rdx
 4e3e32e:	setne	sil
 4e3e332:	test	rcx, rcx
 4e3e335:	sete	cl
 4e3e338:	or	cl, sil
 4e3e33b:	je	0x4e3e342 <.text+0xe36102>
 4e3e33d:	sar	rax
 4e3e340:	pop	rcx
 4e3e341:	ret
 4e3e342:	call	0x4790760 <.text+0x788520>
 4e3e350:	push	rax
 4e3e351:	mov	rax, r8
 4e3e354:	mov	r10, rcx
 4e3e357:	mov	r8, rdx
 4e3e35a:	mov	rdx, rdi
 4e3e35d:	mov	rcx, qword ptr [rsp + 0x18]
 4e3e362:	sub	rsp, 0x8
 4e3e366:	movzx	r11d, byte ptr [rsp + 0x18]
 4e3e36c:	mov	rdi, rsi
 4e3e36f:	mov	rsi, r9
 4e3e372:	mov	r9, r10
 4e3e375:	push	r11
 4e3e377:	push	0x64
 4e3e379:	push	0x1
 4e3e37b:	push	0x1327220
 4e3e380:	push	0x8
 4e3e382:	push	0x18
 4e3e384:	push	rax
 4e3e385:	call	0xd251a10 <.text+0x92497d0>
 4e3e38a:	add	rsp, 0x40
 4e3e38e:	pop	rcx
 4e3e38f:	ret
 4e3e390:	push	rbp
 4e3e391:	push	r15
 4e3e393:	push	r14
 4e3e395:	push	r13
 4e3e397:	push	r12
 4e3e399:	push	rbx
 4e3e39a:	sub	rsp, 0x28
 4e3e39e:	mov	r15, rcx
 4e3e3a1:	mov	r12, rdx
 4e3e3a4:	mov	qword ptr [rsp + 0x10], rsi
 4e3e3a9:	mov	r14, rdi
 4e3e3ac:	mov	rax, qword ptr [rcx]
 4e3e3af:	mov	rcx, rax
 4e3e3b2:	shr	rcx, 0x20
 4e3e3b6:	lea	edx, [rax - 0x17]
 4e3e3b9:	test	eax, eax
 4e3e3bb:	cmovns	edx, eax
 4e3e3be:	lea	esi, [rcx - 0x17]
 4e3e3c1:	test	rax, rax
 4e3e3c4:	cmovns	esi, ecx
 4e3e3c7:	movsxd	rax, edx
 4e3e3ca:	imul	rax, rax, 0x2aaaaaab
 4e3e3d1:	mov	rcx, rax
 4e3e3d4:	shr	rcx, 0x3f
 4e3e3d8:	shr	rax, 0x20
 4e3e3dc:	sar	eax, 0x2
 4e3e3df:	add	eax, ecx
 4e3e3e1:	movsxd	rcx, esi
 4e3e3e4:	imul	rcx, rcx, 0x2aaaaaab
 4e3e3eb:	mov	rdx, rcx
 4e3e3ee:	shr	rdx, 0x3f
 4e3e3f2:	shr	rcx, 0x20
 4e3e3f6:	sar	ecx, 0x2
 4e3e3f9:	add	ecx, edx
 4e3e3fb:	mov	rdx, qword ptr [r12 + 0x9f8]
 4e3e403:	cmp	byte ptr [rdx + 0x9e7], 0x1
 4e3e40a:	jne	0x4e3e4b5 <.text+0xe36275>
 4e3e410:	imul	esi, ecx, 0xf1565bd5
 4e3e416:	imul	edi, eax, 0x9939f508
 4e3e41c:	add	r8d, edi
 4e3e41f:	lea	edi, [rsi + r8]
 4e3e423:	add	edi, 0x1327220
 4e3e429:	mov	dword ptr [rdx + 0x8], edi
 4e3e42c:	mov	word ptr [rdx + 0x9e4], 0x0
 4e3e435:	mov	dword ptr [rdx + 0x9d4], 0x0
 4e3e43f:	mov	qword ptr [rdx + 0x9d8], 0x0
 4e3e44a:	mov	dword ptr [rdx + 0xc], edi
 4e3e44d:	mov	esi, 0x5
 4e3e452:	nop	word ptr cs:[rax + rax]
 4e3e460:	mov	r8d, edi
 4e3e463:	shr	r8d, 0x1e
 4e3e467:	xor	r8d, edi
 4e3e46a:	imul	edi, r8d, 0x6c078965
 4e3e471:	add	rdi, rsi
 4e3e474:	add	rdi, -0x4
 4e3e478:	mov	dword ptr [rdx + 4*rsi - 0x4], edi
 4e3e47c:	cmp	rsi, 0x191
 4e3e483:	je	0x4e3e4a4 <.text+0xe36264>
 4e3e485:	mov	r8d, edi
 4e3e488:	shr	r8d, 0x1e
 4e3e48c:	xor	r8d, edi
 4e3e48f:	imul	edi, r8d, 0x6c078965
 4e3e496:	add	edi, esi
 4e3e498:	add	edi, -0x3
 4e3e49b:	mov	dword ptr [rdx + 4*rsi], edi
 4e3e49e:	add	rsi, 0x2
 4e3e4a2:	jmp	0x4e3e460 <.text+0xe36220>
 4e3e4a4:	movabs	rsi, 0x18e00000270
 4e3e4ae:	mov	qword ptr [rdx + 0x9cc], rsi
 4e3e4b5:	lea	ebx, [rax + 2*rax]
 4e3e4b8:	lea	r13d, [rcx + 2*rcx]
 4e3e4bc:	mov	rax, qword ptr [r12]
 4e3e4c0:	mov	rdi, r12
 4e3e4c3:	mov	esi, 0x10
 4e3e4c8:	call	qword ptr [rax + 0x18]
 4e3e4cb:	mov	ebp, eax
 4e3e4cd:	mov	rax, qword ptr [r12]
 4e3e4d1:	mov	rdi, r12
 4e3e4d4:	mov	esi, 0x10
 4e3e4d9:	call	qword ptr [rax + 0x18]
 4e3e4dc:	add	eax, ebp
 4e3e4de:	mov	ecx, eax
 4e3e4e0:	shr	ecx, 0x1f
 4e3e4e3:	add	ecx, eax
 4e3e4e5:	sar	ecx
 4e3e4e7:	lea	ebx, [rcx + 8*rbx]
 4e3e4ea:	mov	rax, qword ptr [r12]
 4e3e4ee:	mov	rdi, r12
 4e3e4f1:	mov	esi, 0x10
 4e3e4f6:	call	qword ptr [rax + 0x18]
 4e3e4f9:	mov	ebp, eax
 4e3e4fb:	mov	rax, qword ptr [r12]
 4e3e4ff:	mov	rdi, r12
 4e3e502:	mov	esi, 0x10
 4e3e507:	call	qword ptr [rax + 0x18]
 4e3e50a:	add	eax, ebp
 4e3e50c:	mov	ecx, eax
 4e3e50e:	shr	ecx, 0x1f
 4e3e511:	add	ecx, eax
 4e3e513:	sar	ecx
 4e3e515:	lea	eax, [rcx + 8*r13]
 4e3e519:	mov	rcx, qword ptr [r15]
 4e3e51c:	shl	rax, 0x20
 4e3e520:	or	rbx, rax
 4e3e523:	cmp	rcx, rbx
 4e3e526:	jne	0x4e3e592 <.text+0xe36352>
 4e3e528:	mov	rdx, qword ptr [r14 + 0x180]
 4e3e52f:	mov	rax, qword ptr [r14 + 0x188]
 4e3e536:	mov	rsi, rax
 4e3e539:	sub	rsi, rdx
 4e3e53c:	mov	rdi, rsi
 4e3e53f:	sar	rdi
 4e3e542:	mov	qword ptr [rsp + 0x18], rdi
 4e3e547:	cmp	rsi, -0x2
 4e3e54b:	je	0x4e3e5a3 <.text+0xe36363>
 4e3e54d:	mov	qword ptr [rsp + 0x20], rdx
 4e3e552:	test	rdx, rdx
 4e3e555:	setne	dl
 4e3e558:	test	rax, rax
 4e3e55b:	sete	al
 4e3e55e:	or	al, dl
 4e3e560:	je	0x4e3e5a3 <.text+0xe36363>
 4e3e562:	mov	esi, ecx
 4e3e564:	shl	esi, 0x4
 4e3e567:	shr	rcx, 0x1c
 4e3e56b:	and	ecx, -0x10
 4e3e56e:	mov	rdi, qword ptr [rsp + 0x10]
 4e3e573:	mov	rax, qword ptr [rdi]
 4e3e576:	movups	xmm0, xmmword ptr [rsp + 0x18]
 4e3e57b:	movups	xmmword ptr [rsp], xmm0
 4e3e57f:	mov	edx, 0xffffffe5
 4e3e584:	xor	r8d, r8d
 4e3e587:	call	qword ptr [rax + 0x38]
 4e3e58a:	mov	ecx, eax
 4e3e58c:	mov	al, 0x1
 4e3e58e:	test	cl, cl
 4e3e590:	jne	0x4e3e594 <.text+0xe36354>
 4e3e592:	xor	eax, eax
 4e3e594:	add	rsp, 0x28
 4e3e598:	pop	rbx
 4e3e599:	pop	r12
 4e3e59b:	pop	r13
 4e3e59d:	pop	r14
 4e3e59f:	pop	r15
 4e3e5a1:	pop	rbp
 4e3e5a2:	ret
 4e3e5a3:	call	0x4790760 <.text+0x788520>

```

## bastion-check.asm
```asm

/Users/lucasraicu/.local/share/antigravity-worker-mcp/predictor-engine-20261020/bedrock_server:	file format elf64-x86-64

Disassembly of section .text:

0000000004008240 <.text>:
 4e3ec60:	push	rax
 4e3ec61:	mov	rdx, qword ptr [rdi + 0x180]
 4e3ec68:	mov	rcx, qword ptr [rdi + 0x188]
 4e3ec6f:	mov	rax, rcx
 4e3ec72:	sub	rax, rdx
 4e3ec75:	cmp	rax, -0x2
 4e3ec79:	je	0x4e3ec92 <.text+0xe36a52>
 4e3ec7b:	test	rdx, rdx
 4e3ec7e:	setne	sil
 4e3ec82:	test	rcx, rcx
 4e3ec85:	sete	cl
 4e3ec88:	or	cl, sil
 4e3ec8b:	je	0x4e3ec92 <.text+0xe36a52>
 4e3ec8d:	sar	rax
 4e3ec90:	pop	rcx
 4e3ec91:	ret
 4e3ec92:	call	0x4790760 <.text+0x788520>
 4e3eca0:	push	rax
 4e3eca1:	mov	rax, r8
 4e3eca4:	mov	r10, rcx
 4e3eca7:	mov	r8, rdx
 4e3ecaa:	mov	rdx, rdi
 4e3ecad:	mov	rcx, qword ptr [rsp + 0x18]
 4e3ecb2:	sub	rsp, 0x8
 4e3ecb6:	movzx	r11d, byte ptr [rsp + 0x18]
 4e3ecbc:	mov	rdi, rsi
 4e3ecbf:	mov	rsi, r9
 4e3ecc2:	mov	r9, r10
 4e3ecc5:	push	r11
 4e3ecc7:	push	0x64
 4e3ecc9:	push	0x0
 4e3eccb:	push	0x1cb0c88
 4e3ecd0:	push	0x4
 4e3ecd2:	push	0x1e
 4e3ecd4:	push	rax
 4e3ecd5:	call	0xd251a10 <.text+0x92497d0>
 4e3ecda:	add	rsp, 0x40
 4e3ecde:	pop	rcx
 4e3ecdf:	ret
 4e3ece0:	mov	al, 0x1
 4e3ece2:	ret
 4e3ecf0:	push	r15
 4e3ecf2:	push	r14
 4e3ecf4:	push	rbx
 4e3ecf5:	sub	rsp, 0x30
 4e3ecf9:	lea	r9, [rdi + 0x180]
 4e3ed00:	lea	r14, [rsp + 0x8]
 4e3ed05:	mov	rdi, r14
 4e3ed08:	call	0x4fd0b70 <.text+0xfc8930>
 4e3ed0d:	mov	rax, qword ptr [rsp + 0x8]
 4e3ed12:	cmp	rax, qword ptr [rip + 0xa7e083f] # 0xf61f558
 4e3ed19:	jne	0x4e3ed98 <.text+0xe36b58>
 4e3ed1b:	lea	r15, [rip + 0xa7e0836]  # 0xf61f558
 4e3ed22:	cmp	qword ptr [rip + 0xa7e084f], r14 # 0xf61f578
 4e3ed29:	sete	al
 4e3ed2c:	mov	bl, 0x1
 4e3ed2e:	cmp	qword ptr [rsp + 0x28], r15
 4e3ed33:	jne	0x4e3ed39 <.text+0xe36af9>
 4e3ed35:	test	al, al
 4e3ed37:	jne	0x4e3eda3 <.text+0xe36b63>
 4e3ed39:	movzx	eax, byte ptr [rsp + 0x10]
 4e3ed3e:	test	al, 0x1
 4e3ed40:	je	0x4e3ed5e <.text+0xe36b1e>
 4e3ed42:	mov	rdx, qword ptr [rsp + 0x18]
 4e3ed47:	movzx	ecx, byte ptr [rip + 0xa7e0812] # 0xf61f560
 4e3ed4e:	test	cl, 0x1
 4e3ed51:	jne	0x4e3ed6e <.text+0xe36b2e>
 4e3ed53:	mov	esi, ecx
 4e3ed55:	shr	esi
 4e3ed57:	cmp	rdx, rsi
 4e3ed5a:	je	0x4e3ed7a <.text+0xe36b3a>
 4e3ed5c:	jmp	0x4e3ed98 <.text+0xe36b58>
 4e3ed5e:	mov	edx, eax
 4e3ed60:	shr	edx
 4e3ed62:	movzx	ecx, byte ptr [rip + 0xa7e07f7] # 0xf61f560
 4e3ed69:	test	cl, 0x1
 4e3ed6c:	je	0x4e3ed53 <.text+0xe36b13>
 4e3ed6e:	mov	rsi, qword ptr [rip + 0xa7e07f3] # 0xf61f568
 4e3ed75:	cmp	rdx, rsi
 4e3ed78:	jne	0x4e3ed98 <.text+0xe36b58>
 4e3ed7a:	test	al, 0x1
 4e3ed7c:	je	0x4e3edc9 <.text+0xe36b89>
 4e3ed7e:	mov	rdi, qword ptr [rsp + 0x20]
 4e3ed83:	test	cl, 0x1
 4e3ed86:	jne	0x4e3edd3 <.text+0xe36b93>
 4e3ed88:	lea	rsi, [rip + 0xa7e07d2]  # 0xf61f561
 4e3ed8f:	call	0xede3000 <bcmp@plt>
 4e3ed94:	test	eax, eax
 4e3ed96:	je	0x4e3ede3 <.text+0xe36ba3>
 4e3ed98:	mov	qword ptr [rsp + 0x28], 0x0
 4e3eda1:	xor	ebx, ebx
 4e3eda3:	test	byte ptr [rsp + 0x10], 0x1
 4e3eda8:	je	0x4e3edbd <.text+0xe36b7d>
 4e3edaa:	mov	rsi, qword ptr [rsp + 0x10]
 4e3edaf:	mov	rdi, qword ptr [rsp + 0x20]
 4e3edb4:	and	rsi, -0x2
 4e3edb8:	call	0x402a280 <.text+0x22040>
 4e3edbd:	mov	eax, ebx
 4e3edbf:	add	rsp, 0x30
 4e3edc3:	pop	rbx
 4e3edc4:	pop	r14
 4e3edc6:	pop	r15
 4e3edc8:	ret
 4e3edc9:	lea	rdi, [rsp + 0x11]
 4e3edce:	test	cl, 0x1
 4e3edd1:	je	0x4e3ed88 <.text+0xe36b48>
 4e3edd3:	mov	rsi, qword ptr [rip + 0xa7e0796] # 0xf61f570
 4e3edda:	call	0xede3000 <bcmp@plt>
 4e3eddf:	test	eax, eax
 4e3ede1:	jne	0x4e3ed98 <.text+0xe36b58>
 4e3ede3:	mov	qword ptr [rsp + 0x28], r15
 4e3ede8:	mov	qword ptr [rip + 0xa7e0789], r14 # 0xf61f578
 4e3edef:	test	byte ptr [rsp + 0x10], 0x1
 4e3edf4:	jne	0x4e3edaa <.text+0xe36b6a>
 4e3edf6:	jmp	0x4e3edbd <.text+0xe36b7d>

```

## bastion-helper.asm
```asm

/Users/lucasraicu/.local/share/antigravity-worker-mcp/predictor-engine-20261020/bedrock_server:	file format elf64-x86-64

Disassembly of section .text:

0000000004008240 <.text>:
 4fd0b70:	push	rbp
 4fd0b71:	push	r15
 4fd0b73:	push	r14
 4fd0b75:	push	r13
 4fd0b77:	push	r12
 4fd0b79:	push	rbx
 4fd0b7a:	sub	rsp, 0x38
 4fd0b7e:	mov	qword ptr [rsp + 0x20], r9
 4fd0b83:	mov	r13, rcx
 4fd0b86:	mov	r14, rdx
 4fd0b89:	mov	qword ptr [rsp + 0x18], rsi
 4fd0b8e:	mov	rax, qword ptr [rcx]
 4fd0b91:	mov	rcx, rax
 4fd0b94:	shr	rcx, 0x20
 4fd0b98:	lea	edx, [rax - 0x1d]
 4fd0b9b:	test	eax, eax
 4fd0b9d:	cmovns	edx, eax
 4fd0ba0:	lea	esi, [rcx - 0x1d]
 4fd0ba3:	test	rax, rax
 4fd0ba6:	cmovns	esi, ecx
 4fd0ba9:	mov	rbx, rdi
 4fd0bac:	movsxd	r15, edx
 4fd0baf:	imul	rax, r15, -0x77777777
 4fd0bb6:	shr	rax, 0x20
 4fd0bba:	add	r15d, eax
 4fd0bbd:	mov	eax, r15d
 4fd0bc0:	shr	eax, 0x1f
 4fd0bc3:	sar	r15d, 0x4
 4fd0bc7:	add	r15d, eax
 4fd0bca:	movsxd	r12, esi
 4fd0bcd:	imul	rax, r12, -0x77777777
 4fd0bd4:	shr	rax, 0x20
 4fd0bd8:	add	r12d, eax
 4fd0bdb:	mov	eax, r12d
 4fd0bde:	shr	eax, 0x1f
 4fd0be1:	sar	r12d, 0x4
 4fd0be5:	add	r12d, eax
 4fd0be8:	mov	rax, qword ptr [r14 + 0x9f8]
 4fd0bef:	cmp	byte ptr [rax + 0x9e7], 0x1
 4fd0bf6:	jne	0x4fd0c8d <.text+0xfc8a4d>
 4fd0bfc:	imul	ecx, r12d, 0xf1565bd5
 4fd0c03:	imul	edx, r15d, 0x9939f508
 4fd0c0a:	add	r8d, edx
 4fd0c0d:	lea	edx, [rcx + r8]
 4fd0c11:	add	edx, 0x1cb0c88
 4fd0c17:	mov	dword ptr [rax + 0x8], edx
 4fd0c1a:	mov	word ptr [rax + 0x9e4], 0x0
 4fd0c23:	mov	dword ptr [rax + 0x9d4], 0x0
 4fd0c2d:	mov	qword ptr [rax + 0x9d8], 0x0
 4fd0c38:	mov	dword ptr [rax + 0xc], edx
 4fd0c3b:	mov	ecx, 0x5
 4fd0c40:	mov	esi, edx
 4fd0c42:	shr	esi, 0x1e
 4fd0c45:	xor	esi, edx
 4fd0c47:	imul	edx, esi, 0x6c078965
 4fd0c4d:	add	rdx, rcx
 4fd0c50:	add	rdx, -0x4
 4fd0c54:	mov	dword ptr [rax + 4*rcx - 0x4], edx
 4fd0c58:	cmp	rcx, 0x191
 4fd0c5f:	je	0x4fd0c7c <.text+0xfc8a3c>
 4fd0c61:	mov	esi, edx
 4fd0c63:	shr	esi, 0x1e
 4fd0c66:	xor	esi, edx
 4fd0c68:	imul	edx, esi, 0x6c078965
 4fd0c6e:	add	edx, ecx
 4fd0c70:	add	edx, -0x3
 4fd0c73:	mov	dword ptr [rax + 4*rcx], edx
 4fd0c76:	add	rcx, 0x2
 4fd0c7a:	jmp	0x4fd0c40 <.text+0xfc8a00>
 4fd0c7c:	movabs	rcx, 0x18e00000270
 4fd0c86:	mov	qword ptr [rax + 0x9cc], rcx
 4fd0c8d:	lea	eax, [r15 + r15]
 4fd0c91:	shl	r15d, 0x5
 4fd0c95:	sub	r15d, eax
 4fd0c98:	lea	eax, [r12 + r12]
 4fd0c9c:	shl	r12d, 0x5
 4fd0ca0:	sub	r12d, eax
 4fd0ca3:	mov	rax, qword ptr [r14]
 4fd0ca6:	mov	rdi, r14
 4fd0ca9:	mov	esi, 0x1a
 4fd0cae:	call	qword ptr [rax + 0x18]
 4fd0cb1:	mov	ebp, eax
 4fd0cb3:	add	ebp, r15d
 4fd0cb6:	mov	rax, qword ptr [r14]
 4fd0cb9:	mov	rdi, r14
 4fd0cbc:	mov	esi, 0x1a
 4fd0cc1:	call	qword ptr [rax + 0x18]
 4fd0cc4:	add	eax, r12d
 4fd0cc7:	mov	rcx, qword ptr [r13]
 4fd0ccb:	shl	rax, 0x20
 4fd0ccf:	or	rbp, rax
 4fd0cd2:	cmp	rcx, rbp
 4fd0cd5:	jne	0x4fd0db2 <.text+0xfc8b72>
 4fd0cdb:	mov	rax, qword ptr [rsp + 0x20]
 4fd0ce0:	mov	rdx, qword ptr [rax]
 4fd0ce3:	mov	rax, qword ptr [rax + 0x8]
 4fd0ce7:	mov	rsi, rax
 4fd0cea:	sub	rsi, rdx
 4fd0ced:	mov	rdi, rsi
 4fd0cf0:	sar	rdi
 4fd0cf3:	mov	qword ptr [rsp + 0x28], rdi
 4fd0cf8:	cmp	rsi, -0x2
 4fd0cfc:	je	0x4fd0e13 <.text+0xfc8bd3>
 4fd0d02:	mov	qword ptr [rsp + 0x30], rdx
 4fd0d07:	test	rdx, rdx
 4fd0d0a:	setne	dl
 4fd0d0d:	test	rax, rax
 4fd0d10:	sete	al
 4fd0d13:	or	al, dl
 4fd0d15:	je	0x4fd0e13 <.text+0xfc8bd3>
 4fd0d1b:	mov	esi, ecx
 4fd0d1d:	shl	esi, 0x4
 4fd0d20:	shr	rcx, 0x1c
 4fd0d24:	and	ecx, -0x10
 4fd0d27:	mov	rdi, qword ptr [rsp + 0x18]
 4fd0d2c:	mov	rax, qword ptr [rdi]
 4fd0d2f:	movups	xmm0, xmmword ptr [rsp + 0x28]
 4fd0d34:	movups	xmmword ptr [rsp], xmm0
 4fd0d38:	mov	edx, 0x1
 4fd0d3d:	mov	r8d, 0x2
 4fd0d43:	call	qword ptr [rax + 0x38]
 4fd0d46:	test	al, al
 4fd0d48:	je	0x4fd0db2 <.text+0xfc8b72>
 4fd0d4a:	mov	rax, qword ptr [r14]
 4fd0d4d:	mov	rdi, r14
 4fd0d50:	mov	esi, 0x6
 4fd0d55:	call	qword ptr [rax + 0x18]
 4fd0d58:	cmp	eax, 0x2
 4fd0d5b:	lea	rcx, [rip + 0xa64e9e6]  # 0xf61f748
 4fd0d62:	lea	r15, [rip + 0xa64e7ef]  # 0xf61f558
 4fd0d69:	cmovl	r15, rcx
 4fd0d6d:	lea	rdx, [rip + 0xa64e9dc]  # 0xf61f750
 4fd0d74:	lea	rcx, [rip + 0xa64e7e5]  # 0xf61f560
 4fd0d7b:	cmovl	rcx, rdx
 4fd0d7f:	xorps	xmm0, xmm0
 4fd0d82:	movups	xmmword ptr [rbx], xmm0
 4fd0d85:	movups	xmmword ptr [rbx + 0x10], xmm0
 4fd0d89:	mov	qword ptr [rbx + 0x20], 0x0
 4fd0d91:	cmp	rbx, r15
 4fd0d94:	je	0x4fd0dfb <.text+0xfc8bbb>
 4fd0d96:	lea	r14, [rbx + 0x8]
 4fd0d9a:	test	byte ptr [r15 + 0x8], 0x1
 4fd0d9f:	jne	0x4fd0dc6 <.text+0xfc8b86>
 4fd0da1:	mov	rax, qword ptr [rcx + 0x10]
 4fd0da5:	mov	qword ptr [r14 + 0x10], rax
 4fd0da9:	movups	xmm0, xmmword ptr [rcx]
 4fd0dac:	movups	xmmword ptr [r14], xmm0
 4fd0db0:	jmp	0x4fd0dfb <.text+0xfc8bbb>
 4fd0db2:	xorps	xmm0, xmm0
 4fd0db5:	movups	xmmword ptr [rbx + 0x10], xmm0
 4fd0db9:	movups	xmmword ptr [rbx], xmm0
 4fd0dbc:	mov	qword ptr [rbx + 0x20], 0x0
 4fd0dc4:	jmp	0x4fd0e01 <.text+0xfc8bc1>
 4fd0dc6:	cmp	eax, 0x2
 4fd0dc9:	lea	rax, [rip + 0xa64e990]  # 0xf61f760
 4fd0dd0:	lea	rcx, [rip + 0xa64e799]  # 0xf61f570
 4fd0dd7:	cmovl	rcx, rax
 4fd0ddb:	mov	rsi, qword ptr [rcx]
 4fd0dde:	lea	rax, [rip + 0xa64e973]  # 0xf61f758
 4fd0de5:	lea	rcx, [rip + 0xa64e77c]  # 0xf61f568
 4fd0dec:	cmovl	rcx, rax
 4fd0df0:	mov	rdx, qword ptr [rcx]
 4fd0df3:	mov	rdi, r14
 4fd0df6:	call	0x4785070 <.text+0x77ce30>
 4fd0dfb:	mov	rax, qword ptr [r15]
 4fd0dfe:	mov	qword ptr [rbx], rax
 4fd0e01:	mov	rax, rbx
 4fd0e04:	add	rsp, 0x38
 4fd0e08:	pop	rbx
 4fd0e09:	pop	r12
 4fd0e0b:	pop	r13
 4fd0e0d:	pop	r14
 4fd0e0f:	pop	r15
 4fd0e11:	pop	rbp
 4fd0e12:	ret
 4fd0e13:	call	0x4790760 <.text+0x788520>
 4fd0e18:	mov	r15, rax
 4fd0e1b:	test	byte ptr [r14], 0x1
 4fd0e1f:	je	0x4fd0e32 <.text+0xfc8bf2>
 4fd0e21:	mov	rsi, qword ptr [rbx + 0x8]
 4fd0e25:	mov	rdi, qword ptr [rbx + 0x18]
 4fd0e29:	and	rsi, -0x2
 4fd0e2d:	call	0x402a280 <.text+0x22040>
 4fd0e32:	mov	rdi, r15
 4fd0e35:	call	0xede2d70 <_Unwind_Resume@plt>
 4fd0e40:	push	rbp
 4fd0e41:	push	r15
 4fd0e43:	push	r14
 4fd0e45:	push	r13
 4fd0e47:	push	r12
 4fd0e49:	push	rbx
 4fd0e4a:	sub	rsp, 0x538
 4fd0e51:	mov	r15, r8
 4fd0e54:	mov	r12, rcx
 4fd0e57:	mov	rbx, rdx
 4fd0e5a:	mov	r13, rsi
 4fd0e5d:	mov	rbp, rdi
 4fd0e60:	mov	rax, qword ptr [rdi]
 4fd0e63:	mov	qword ptr [rsp + 0x110], rax
 4fd0e6b:	mov	rcx, qword ptr [rdi + 0x8]
 4fd0e6f:	mov	qword ptr [rsp + 0x118], rcx
 4fd0e77:	test	rcx, rcx
 4fd0e7a:	je	0x4fd0e81 <.text+0xfc8c41>
 4fd0e7c:	lock
 4fd0e7d:	inc	qword ptr [rcx + 0x8]
 4fd0e81:	mov	rcx, qword ptr [rbp + 0x10]
 4fd0e85:	mov	qword ptr [rsp + 0x120], rcx
 4fd0e8d:	test	rax, rax
 4fd0e90:	je	0x4fd237f <.text+0xfca13f>
 4fd0e96:	cmp	byte ptr [rax], 0x0
 4fd0e99:	je	0x4fd237f <.text+0xfca13f>
 4fd0e9f:	lea	rax, [rbx + 0x110]
 4fd0ea6:	mov	qword ptr [rsp + 0x128], rax
 4fd0eae:	mov	qword ptr [rsp + 0x130], r13
 4fd0eb6:	lea	r14, [rsp + 0x138]
 4fd0ebe:	mov	rdi, r14
 4fd0ec1:	mov	rsi, r12
 4fd0ec4:	call	0xd78e390 <.text+0x9786150>
 4fd0ec9:	mov	qword ptr [rsp + 0x158], r15

```

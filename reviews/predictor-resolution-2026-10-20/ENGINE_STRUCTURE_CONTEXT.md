# Pinned BDS static control-flow context

Read-only investigation. Binary SHA256 0a490c711d4a2ce075debcd979e8862b7eaba008373f9970f0edbb67f98f9207, BDS1.26.52.3. RTTI recovers class identity, but generated headers describe another build/platform and their declaration order does NOT determine Linux vtable slot order. Infer function roles from control flow. Calls to biomeSource vtable+0x38 need resolving; preliminarySurfaceProvider vtable+0x10 returns a packed optional int16. No slope threshold justified.

```asm
 4fbba0c:      	mov	r12, rbx
 4fbba0f:      	shr	r12, 0x1c
 4fbba13:      	and	r12d, -0x10
 4fbba17:      	lea	esi, [4*rbx]
 4fbba1e:      	mov	eax, r12d
 4fbba21:      	sar	eax, 0x2
 4fbba24:      	shl	rax, 0x20
 4fbba28:      	or	rsi, rax
 4fbba2b:      	mov	rdi, qword ptr [rsp + 0x20]
 4fbba30:      	mov	rax, qword ptr [rdi]
 4fbba33:      	call	qword ptr [rax + 0x10]
 4fbba36:      	test	eax, 0x10000
 4fbba3b:      	cwde
 4fbba3c:      	mov	edx, 0x1
 4fbba41:      	cmovne	edx, eax
 4fbba44:      	mov	rcx, qword ptr [r14 + 0x188]
 4fbba4b:      	mov	rax, qword ptr [r14 + 0x190]
 4fbba52:      	mov	rsi, rax
 4fbba55:      	sub	rsi, rcx
 4fbba58:      	mov	rdi, rsi
 4fbba5b:      	sar	rdi
 4fbba5e:      	mov	qword ptr [rsp + 0x28], rdi
 4fbba63:      	cmp	rsi, -0x2
 4fbba67:      	je	0x4fbbac0 <.text+0xfb3880>
 4fbba69:      	mov	qword ptr [rsp + 0x30], rcx
 4fbba6e:      	test	rcx, rcx
 4fbba71:      	setne	cl
 4fbba74:      	test	rax, rax
 4fbba77:      	sete	al
 4fbba7a:      	or	al, cl
 4fbba7c:      	je	0x4fbbac0 <.text+0xfb3880>
 4fbba7e:      	or	r12d, 0x8
 4fbba82:      	shl	ebx, 0x4
 4fbba85:      	or	ebx, 0x8
 4fbba88:      	mov	rdi, qword ptr [rsp + 0x18]
 4fbba8d:      	mov	rax, qword ptr [rdi]
 4fbba90:      	movups	xmm0, xmmword ptr [rsp + 0x28]
 4fbba95:      	movups	xmmword ptr [rsp], xmm0
 4fbba99:      	mov	esi, ebx
 4fbba9b:      	mov	ecx, r12d
 4fbba9e:      	mov	r8d, 0x2
 4fbbaa4:      	call	qword ptr [rax + 0x38]
 4fbbaa7:      	mov	ecx, eax
 4e832ac:      	mov	r12, rbx
 4e832af:      	shr	r12, 0x1c
 4e832b3:      	and	r12d, -0x10
 4e832b7:      	lea	esi, [4*rbx]
 4e832be:      	mov	eax, r12d
 4e832c1:      	sar	eax, 0x2
 4e832c4:      	shl	rax, 0x20
 4e832c8:      	or	rsi, rax
 4e832cb:      	mov	rdi, qword ptr [rsp + 0x20]
 4e832d0:      	mov	rax, qword ptr [rdi]
 4e832d3:      	call	qword ptr [rax + 0x10]
 4e832d6:      	test	eax, 0x10000
 4e832db:      	cwde
 4e832dc:      	mov	edx, 0x1
 4e832e1:      	cmovne	edx, eax
 4e832e4:      	mov	rcx, qword ptr [r14 + 0x188]
 4e832eb:      	mov	rax, qword ptr [r14 + 0x190]
 4e832f2:      	mov	rsi, rax
 4e832f5:      	sub	rsi, rcx
 4e832f8:      	mov	rdi, rsi
 4e832fb:      	sar	rdi
 4e832fe:      	mov	qword ptr [rsp + 0x28], rdi
 4e83303:      	cmp	rsi, -0x2
 4e83307:      	je	0x4e8335d <.text+0xe7b11d>
 4e83309:      	mov	qword ptr [rsp + 0x30], rcx
 4e8330e:      	test	rcx, rcx
 4e83311:      	setne	cl
 4e83314:      	test	rax, rax
 4e83317:      	sete	al
 4e8331a:      	or	al, cl
 4e8331c:      	je	0x4e8335d <.text+0xe7b11d>
 4e8331e:      	or	r12d, 0x8
 4e83322:      	shl	ebx, 0x4
 4e83325:      	or	ebx, 0x8
 4e83328:      	mov	rdi, qword ptr [rsp + 0x18]
 4e8332d:      	mov	rax, qword ptr [rdi]
 4e83330:      	movups	xmm0, xmmword ptr [rsp + 0x28]
 4e83335:      	movups	xmmword ptr [rsp], xmm0
 4e83339:      	mov	esi, ebx
 4e8333b:      	mov	ecx, r12d
 4e8333e:      	xor	r8d, r8d
 4e83341:      	call	qword ptr [rax + 0x38]
 4e83344:      	mov	ecx, eax
 4e83346:      	mov	al, 0x1
 4e83348:      	test	cl, cl
 4e8334a:      	jne	0x4e8334e <.text+0xe7b10e>
```

Village createStructureStart includes call biomeSource+0x58 with centerX=(cx<<4)+8,Y=preliminaryHeight or1,centerZ=(cz<<4)+8 and optionbyte1; biome atreturnedobject+0x170 tags is used toselectvillage variant. No conclusions about general rejection yet.

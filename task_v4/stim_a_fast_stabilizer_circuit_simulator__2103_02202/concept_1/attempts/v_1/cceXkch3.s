	.file	"engine.cpp"
	.text
	.section	.text._ZN9__gnu_cxx13new_allocatorI5StateE8allocateEmPKv.constprop.0,"axG",@progbits,_ZN9Optimizer3runEv,comdat
	.align 2
	.p2align 4
	.type	_ZN9__gnu_cxx13new_allocatorI5StateE8allocateEmPKv.constprop.0, @function
_ZN9__gnu_cxx13new_allocatorI5StateE8allocateEmPKv.constprop.0:
.LFB8833:
	.cfi_startproc
	movq	%rdi, %rax
	shrq	$59, %rax
	jne	.L8
	salq	$4, %rdi
	jmp	_Znwm@PLT
	.p2align 4
	.p2align 3
.L8:
	subq	$8, %rsp
	.cfi_def_cfa_offset 16
	shrq	$60, %rdi
	je	.L3
	call	_ZSt28__throw_bad_array_new_lengthv@PLT
	.p2align 4
	.p2align 3
.L3:
	call	_ZSt17__throw_bad_allocv@PLT
	.cfi_endproc
.LFE8833:
	.size	_ZN9__gnu_cxx13new_allocatorI5StateE8allocateEmPKv.constprop.0, .-_ZN9__gnu_cxx13new_allocatorI5StateE8allocateEmPKv.constprop.0
	.section	.text._ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_T0_SJ_T1_T2_.isra.0,"axG",@progbits,_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_,comdat
	.p2align 4
	.type	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_T0_SJ_T1_T2_.isra.0, @function
_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_T0_SJ_T1_T2_.isra.0:
.LFB8835:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	movq	%rdx, %rbp
	movq	%rdx, %r9
	subq	$136, %rsp
	.cfi_def_cfa_offset 160
	andl	$1, %ebp
	movq	%fs:40, %rax
	movq	%rax, 120(%rsp)
	xorl	%eax, %eax
	leaq	-1(%rdx), %rax
	vmovsd	176(%rsp), %xmm0
	movq	%rax, %r10
	shrq	$63, %r10
	addq	%rax, %r10
	sarq	%r10
	cmpq	%r10, %rsi
	jge	.L10
	movq	%rsi, %rbx
	jmp	.L14
	.p2align 4
	.p2align 3
.L31:
	vmovdqa	(%rdx), %xmm2
	leaq	(%rbx,%rbx,2), %rax
	movq	%r8, %rcx
	salq	$5, %rax
	addq	%rdi, %rax
	vmovdqa	%xmm2, (%rax)
	vmovdqa	16(%rdx), %xmm3
	vmovdqa	%xmm3, 16(%rax)
	vmovdqa	32(%rdx), %xmm4
	vmovdqa	%xmm4, 32(%rax)
	vmovdqa	48(%rdx), %xmm5
	vmovdqa	%xmm5, 48(%rax)
	vmovdqa	64(%rdx), %xmm6
	vmovdqa	%xmm6, 64(%rax)
	vmovdqa	80(%rdx), %xmm7
	vmovdqa	%xmm7, 80(%rax)
	cmpq	%r8, %r10
	jle	.L30
.L12:
	movq	%rcx, %rbx
.L14:
	leaq	1(%rbx), %rdx
	leaq	(%rdx,%rdx), %r8
	leaq	(%r8,%rdx,4), %rdx
	leaq	-3(%r8,%r8,2), %r11
	leaq	-1(%r8), %rcx
	salq	$5, %rdx
	salq	$5, %r11
	addq	%rdi, %rdx
	leaq	(%rdi,%r11), %rax
	vmovsd	16(%rdx), %xmm1
	vcomisd	16(%rdi,%r11), %xmm1
	jbe	.L31
	vmovdqa	(%rax), %xmm2
	leaq	(%rbx,%rbx,2), %rdx
	salq	$5, %rdx
	addq	%rdi, %rdx
	vmovdqa	%xmm2, (%rdx)
	vmovdqa	16(%rax), %xmm3
	vmovdqa	%xmm3, 16(%rdx)
	vmovdqa	32(%rax), %xmm4
	vmovdqa	%xmm4, 32(%rdx)
	vmovdqa	48(%rax), %xmm5
	vmovdqa	%xmm5, 48(%rdx)
	vmovdqa	64(%rax), %xmm6
	vmovdqa	%xmm6, 64(%rdx)
	vmovdqa	80(%rax), %xmm7
	vmovdqa	%xmm7, 80(%rdx)
	cmpq	%rcx, %r10
	jg	.L12
	testq	%rbp, %rbp
	je	.L19
.L15:
	vmovdqa	160(%rsp), %xmm2
	vmovdqa	176(%rsp), %xmm3
	leaq	-1(%rcx), %rdx
	vmovdqa	192(%rsp), %xmm4
	vmovdqa	208(%rsp), %xmm5
	movq	%rdx, %r8
	vmovdqa	224(%rsp), %xmm6
	vmovdqa	240(%rsp), %xmm7
	shrq	$63, %r8
	addq	%rdx, %r8
	sarq	%r8
	vmovdqa	%xmm2, (%rsp)
	vmovdqa	%xmm3, 16(%rsp)
	vmovdqa	%xmm4, 32(%rsp)
	vmovdqa	%xmm5, 48(%rsp)
	vmovdqa	%xmm6, 64(%rsp)
	vmovdqa	%xmm7, 80(%rsp)
	cmpq	%rsi, %rcx
	jg	.L18
	jmp	.L16
	.p2align 4
	.p2align 3
.L33:
	vmovdqa	(%rdx), %xmm2
	leaq	-1(%r8), %rcx
	vmovdqa	%xmm2, (%rax)
	vmovdqa	16(%rdx), %xmm3
	vmovdqa	%xmm3, 16(%rax)
	vmovdqa	32(%rdx), %xmm4
	vmovdqa	%xmm4, 32(%rax)
	vmovdqa	48(%rdx), %xmm5
	vmovdqa	%xmm5, 48(%rax)
	vmovdqa	64(%rdx), %xmm6
	vmovdqa	%xmm6, 64(%rax)
	vmovdqa	80(%rdx), %xmm7
	vmovdqa	%xmm7, 80(%rax)
	movq	%rcx, %rax
	shrq	$63, %rax
	addq	%rcx, %rax
	movq	%r8, %rcx
	sarq	%rax
	cmpq	%r8, %rsi
	jge	.L32
	movq	%rax, %r8
.L18:
	leaq	(%r8,%r8,2), %rdx
	leaq	(%rcx,%rcx,2), %rax
	salq	$5, %rdx
	salq	$5, %rax
	addq	%rdi, %rdx
	addq	%rdi, %rax
	vmovsd	16(%rdx), %xmm1
	vcomisd	%xmm0, %xmm1
	ja	.L33
.L16:
	vmovsd	%xmm0, 16(%rsp)
	vmovdqa	(%rsp), %xmm0
	vmovdqa	%xmm0, (%rax)
	vmovdqa	16(%rsp), %xmm0
	vmovdqa	%xmm0, 16(%rax)
	vmovdqa	32(%rsp), %xmm0
	vmovdqa	%xmm0, 32(%rax)
	vmovdqa	48(%rsp), %xmm0
	vmovdqa	%xmm0, 48(%rax)
	vmovdqa	64(%rsp), %xmm0
	vmovdqa	%xmm0, 64(%rax)
	vmovdqa	80(%rsp), %xmm0
	vmovdqa	%xmm0, 80(%rax)
	movq	120(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L34
	addq	$136, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L10:
	.cfi_restore_state
	leaq	(%rsi,%rsi,2), %rax
	salq	$5, %rax
	addq	%rdi, %rax
	testq	%rbp, %rbp
	jne	.L35
	movq	%rsi, %rcx
	.p2align 4
	.p2align 3
.L19:
	subq	$2, %r9
	movq	%r9, %rdx
	shrq	$63, %rdx
	addq	%r9, %rdx
	sarq	%rdx
	cmpq	%rcx, %rdx
	jne	.L15
	leaq	1(%rcx,%rcx), %rcx
	leaq	(%rcx,%rcx,2), %rdx
	salq	$5, %rdx
	addq	%rdi, %rdx
	vmovdqa	(%rdx), %xmm1
	vmovdqa	%xmm1, (%rax)
	vmovdqa	16(%rdx), %xmm1
	vmovdqa	%xmm1, 16(%rax)
	vmovdqa	32(%rdx), %xmm1
	vmovdqa	%xmm1, 32(%rax)
	vmovdqa	48(%rdx), %xmm2
	vmovdqa	%xmm2, 48(%rax)
	vmovdqa	64(%rdx), %xmm3
	vmovdqa	%xmm3, 64(%rax)
	vmovdqa	80(%rdx), %xmm4
	vmovdqa	%xmm4, 80(%rax)
	movq	%rdx, %rax
	jmp	.L15
	.p2align 4
	.p2align 3
.L32:
	movq	%rdx, %rax
	jmp	.L16
	.p2align 4
	.p2align 3
.L30:
	movq	%rdx, %rax
	testq	%rbp, %rbp
	jne	.L15
	jmp	.L19
.L35:
	vmovdqa	160(%rsp), %xmm5
	vmovdqa	176(%rsp), %xmm6
	vmovdqa	192(%rsp), %xmm7
	vmovdqa	%xmm5, (%rsp)
	vmovdqa	%xmm6, 16(%rsp)
	vmovdqa	208(%rsp), %xmm5
	vmovdqa	224(%rsp), %xmm6
	vmovdqa	%xmm7, 32(%rsp)
	vmovdqa	240(%rsp), %xmm7
	vmovdqa	%xmm5, 48(%rsp)
	vmovdqa	%xmm6, 64(%rsp)
	vmovdqa	%xmm7, 80(%rsp)
	jmp	.L16
.L34:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE8835:
	.size	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_T0_SJ_T1_T2_.isra.0, .-_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_T0_SJ_T1_T2_.isra.0
	.section	.text._ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_less_iterEEvT_T0_SC_T1_T2_.isra.0,"axG",@progbits,_ZN9Optimizer14informed_seedsEv,comdat
	.p2align 4
	.type	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_less_iterEEvT_T0_SC_T1_T2_.isra.0, @function
_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_less_iterEEvT_T0_SC_T1_T2_.isra.0:
.LFB8837:
	.cfi_startproc
	leaq	-1(%rdx), %rax
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	movq	%rdx, %r13
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	movq	%rax, %r10
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	movq	%rsi, %r8
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	shrq	$63, %r10
	movq	%rdx, %r9
	vmovsd	%xmm0, %xmm0, %xmm2
	movl	%ecx, %r12d
	addq	%rax, %r10
	andl	$1, %r13d
	sarq	%r10
	cmpq	%r10, %rsi
	jge	.L37
	movq	%rsi, %rcx
	jmp	.L40
	.p2align 4
	.p2align 3
.L62:
	movl	8(%rax), %r11d
	vcomisd	%xmm0, %xmm1
	ja	.L49
	movl	8(%rdx), %ebp
	cmpl	%r11d, %ebp
	jle	.L49
	movl	%ebp, %r11d
	.p2align 4
	.p2align 3
.L39:
	salq	$4, %rcx
	addq	%rdi, %rcx
	vmovsd	%xmm0, (%rcx)
	movl	%r11d, 8(%rcx)
	cmpq	%rsi, %r10
	jle	.L61
	movq	%rsi, %rcx
.L40:
	leaq	1(%rcx), %rax
	leaq	(%rax,%rax), %rbx
	salq	$5, %rax
	leaq	-1(%rbx), %rsi
	addq	%rdi, %rax
	movq	%rsi, %rdx
	vmovsd	(%rax), %xmm1
	salq	$4, %rdx
	addq	%rdi, %rdx
	vmovsd	(%rdx), %xmm0
	vcomisd	%xmm1, %xmm0
	jbe	.L62
	movl	8(%rdx), %r11d
	jmp	.L39
	.p2align 4
	.p2align 3
.L49:
	vmovsd	%xmm1, %xmm1, %xmm0
	movq	%rax, %rdx
	movq	%rbx, %rsi
	jmp	.L39
	.p2align 4
	.p2align 3
.L61:
	testq	%r13, %r13
	je	.L48
.L41:
	leaq	-1(%rsi), %rcx
	movq	%rcx, %rax
	shrq	$63, %rax
	addq	%rcx, %rax
	sarq	%rax
	cmpq	%r8, %rsi
	jle	.L43
.L42:
	movq	%rax, %rdx
	salq	$4, %rdx
	addq	%rdi, %rdx
	vmovsd	(%rdx), %xmm0
	vcomisd	%xmm0, %xmm2
	ja	.L44
	vcomisd	%xmm2, %xmm0
	ja	.L60
	movl	8(%rdx), %ecx
	cmpl	%ecx, %r12d
	jle	.L60
.L47:
	salq	$4, %rsi
	addq	%rdi, %rsi
	movl	%ecx, 8(%rsi)
	vmovsd	%xmm0, (%rsi)
	leaq	-1(%rax), %rsi
	movq	%rsi, %rcx
	shrq	$63, %rcx
	addq	%rsi, %rcx
	movq	%rax, %rsi
	sarq	%rcx
	cmpq	%rax, %r8
	jge	.L43
	movq	%rcx, %rax
	jmp	.L42
	.p2align 4
	.p2align 3
.L37:
	movq	%rsi, %rdx
	salq	$4, %rdx
	addq	%rdi, %rdx
	testq	%r13, %r13
	jne	.L43
	.p2align 4
	.p2align 3
.L48:
	subq	$2, %r9
	movq	%r9, %rax
	shrq	$63, %rax
	addq	%r9, %rax
	sarq	%rax
	cmpq	%rsi, %rax
	jne	.L41
	leaq	1(%rsi,%rsi), %rsi
	movq	%rsi, %rax
	salq	$4, %rax
	addq	%rdi, %rax
	vmovsd	(%rax), %xmm0
	movl	8(%rax), %ecx
	movl	%ecx, 8(%rdx)
	vmovsd	%xmm0, (%rdx)
	movq	%rax, %rdx
	jmp	.L41
	.p2align 4
	.p2align 3
.L60:
	salq	$4, %rsi
	leaq	(%rdi,%rsi), %rdx
.L43:
	vmovsd	%xmm2, (%rdx)
	movl	%r12d, 8(%rdx)
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L44:
	.cfi_restore_state
	movl	8(%rdx), %ecx
	jmp	.L47
	.cfi_endproc
.LFE8837:
	.size	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_less_iterEEvT_T0_SC_T1_T2_.isra.0, .-_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_less_iterEEvT_T0_SC_T1_T2_.isra.0
	.text
	.p2align 4
	.type	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_less_iterEEvT_T0_SB_T1_T2_.constprop.0, @function
_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_less_iterEEvT_T0_SB_T1_T2_.constprop.0:
.LFB8839:
	.cfi_startproc
	leaq	-1(%rsi), %rax
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	movq	%rsi, %rbx
	movq	%rax, %r10
	vmovsd	%xmm0, %xmm0, %xmm2
	andl	$1, %ebx
	shrq	$63, %r10
	addq	%rax, %r10
	sarq	%r10
	cmpq	$2, %rsi
	jle	.L64
	movq	%rsi, %r11
	xorl	%esi, %esi
	jmp	.L70
	.p2align 4
	.p2align 3
.L65:
	movq	8(%r8), %r14
	cmpq	%r14, 8(%rcx)
	jnb	.L68
.L67:
	vmovdqu	(%r8), %xmm3
	salq	$4, %rsi
	vmovdqu	%xmm3, (%rdi,%rsi)
	cmpq	%r10, %rax
	jge	.L69
.L79:
	movq	%rax, %rsi
.L70:
	leaq	1(%rsi), %rcx
	leaq	(%rcx,%rcx), %r9
	salq	$5, %rcx
	leaq	-1(%r9), %rax
	addq	%rdi, %rcx
	movq	%rax, %r8
	vmovsd	(%rcx), %xmm0
	salq	$4, %r8
	addq	%rdi, %r8
	vmovsd	(%r8), %xmm1
	vucomisd	%xmm1, %xmm0
	jp	.L86
	je	.L65
.L86:
	vcomisd	%xmm0, %xmm1
	ja	.L67
.L68:
	vmovdqu	(%rcx), %xmm4
	salq	$4, %rsi
	vmovdqu	%xmm4, (%rdi,%rsi)
	cmpq	%r10, %r9
	jge	.L94
	movq	%r9, %rax
	jmp	.L79
.L94:
	movq	%rcx, %r8
	movq	%r9, %rax
.L69:
	testq	%rbx, %rbx
	je	.L81
	leaq	-1(%rax), %r9
	sarq	%r9
	jmp	.L78
	.p2align 4
	.p2align 3
.L75:
	cmpq	%rdx, 8(%rcx)
	jnb	.L93
.L77:
	vmovdqu	(%rcx), %xmm5
	salq	$4, %rax
	leaq	-1(%r9), %rsi
	vmovdqu	%xmm5, (%rdi,%rax)
	movq	%rsi, %rax
	shrq	$63, %rax
	addq	%rax, %rsi
	movq	%r9, %rax
	sarq	%rsi
	testq	%r9, %r9
	je	.L72
	movq	%rsi, %r9
.L78:
	movq	%r9, %rcx
	salq	$4, %rcx
	addq	%rdi, %rcx
	vmovsd	(%rcx), %xmm0
	vucomisd	%xmm2, %xmm0
	jp	.L87
	je	.L75
.L87:
	vcomisd	%xmm0, %xmm2
	ja	.L77
.L93:
	salq	$4, %rax
	leaq	(%rdi,%rax), %rcx
.L72:
	vmovsd	%xmm2, (%rcx)
	movq	%rdx, 8(%rcx)
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L81:
	.cfi_restore_state
	subq	$2, %r11
	leaq	-1(%rax), %r9
	sarq	%r11
	sarq	%r9
	cmpq	%rax, %r11
	jne	.L78
.L71:
	leaq	2(%rax,%rax), %r9
	leaq	-1(%r9), %rax
	subq	$2, %r9
	movq	%rax, %rcx
	sarq	%r9
	salq	$4, %rcx
	vmovdqu	(%rdi,%rcx), %xmm6
	vmovdqu	%xmm6, (%r8)
	jmp	.L78
	.p2align 4
	.p2align 3
.L64:
	testq	%rbx, %rbx
	jne	.L92
	cmpq	$2, %rax
	jbe	.L83
.L92:
	movq	%rdi, %rcx
	jmp	.L72
.L83:
	movq	%rdi, %r8
	xorl	%eax, %eax
	jmp	.L71
	.cfi_endproc
.LFE8839:
	.size	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_less_iterEEvT_T0_SB_T1_T2_.constprop.0, .-_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_less_iterEEvT_T0_SB_T1_T2_.constprop.0
	.section	.text._ZNKSt6vectorI5StateSaIS0_EE12_M_check_lenEmPKc.isra.0,"axG",@progbits,_ZN9Optimizer3runEv,comdat
	.align 2
	.p2align 4
	.type	_ZNKSt6vectorI5StateSaIS0_EE12_M_check_lenEmPKc.isra.0, @function
_ZNKSt6vectorI5StateSaIS0_EE12_M_check_lenEmPKc.isra.0:
.LFB8841:
	.cfi_startproc
	subq	%rdi, %rsi
	movabsq	$576460752303423487, %rax
	sarq	$4, %rsi
	movq	%rax, %rdi
	subq	%rsi, %rdi
	cmpq	%rdx, %rdi
	jb	.L104
	cmpq	%rdx, %rsi
	cmovnb	%rsi, %rdx
	addq	%rdx, %rsi
	jc	.L95
	movabsq	$576460752303423487, %rax
	cmpq	%rax, %rsi
	cmovbe	%rsi, %rax
.L95:
	ret
.L104:
	movq	%rcx, %rdi
	pushq	%rax
	.cfi_def_cfa_offset 16
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE8841:
	.size	_ZNKSt6vectorI5StateSaIS0_EE12_M_check_lenEmPKc.isra.0, .-_ZNKSt6vectorI5StateSaIS0_EE12_M_check_lenEmPKc.isra.0
	.text
	.p2align 4
	.type	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0, @function
_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0:
.LFB8843:
	.cfi_startproc
	cmpq	%rsi, %rdi
	je	.L126
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	pushq	%r13
	.cfi_def_cfa_offset 24
	.cfi_offset 13, -24
	pushq	%r12
	.cfi_def_cfa_offset 32
	.cfi_offset 12, -32
	movq	%rsi, %r14
	pushq	%rbp
	.cfi_def_cfa_offset 40
	.cfi_offset 6, -40
	pushq	%rbx
	.cfi_def_cfa_offset 48
	.cfi_offset 3, -48
	leaq	16(%rdi), %rbx
	movq	%rdi, %rbp
	subq	$16, %rsp
	.cfi_def_cfa_offset 64
	cmpq	%rbx, %rsi
	je	.L124
	movl	$16, %r12d
	jmp	.L119
	.p2align 4
	.p2align 3
.L108:
	cmpq	%r13, 8(%rbp)
	jbe	.L120
.L110:
	cmpq	%rbx, %rbp
	je	.L112
	movq	%rbx, %rdx
	leaq	0(%rbp,%r12), %rdi
	movq	%rbp, %rsi
	vmovsd	%xmm0, 8(%rsp)
	subq	%rbp, %rdx
	call	memmove@PLT
	vmovsd	8(%rsp), %xmm0
.L112:
	addq	$16, %rbx
	vmovsd	%xmm0, 0(%rbp)
	movq	%r13, 8(%rbp)
	cmpq	%rbx, %r14
	je	.L124
.L119:
	vmovsd	(%rbx), %xmm0
	vmovsd	0(%rbp), %xmm1
	movq	8(%rbx), %r13
	vucomisd	%xmm1, %xmm0
	jp	.L121
	je	.L108
.L121:
	vcomisd	%xmm0, %xmm1
	ja	.L110
.L120:
	movq	%rbx, %rax
	jmp	.L114
	.p2align 4
	.p2align 3
.L115:
	subq	$16, %rax
	cmpq	%r13, -8(%rdx)
	jbe	.L118
.L117:
	vmovdqu	(%rax), %xmm2
	vmovdqu	%xmm2, 16(%rax)
.L114:
	vmovsd	-16(%rax), %xmm1
	movq	%rax, %rdx
	vucomisd	%xmm1, %xmm0
	jp	.L122
	je	.L115
.L122:
	subq	$16, %rax
	vcomisd	%xmm0, %xmm1
	ja	.L117
.L118:
	addq	$16, %rbx
	vmovsd	%xmm0, (%rdx)
	movq	%r13, 8(%rdx)
	cmpq	%rbx, %r14
	jne	.L119
.L124:
	addq	$16, %rsp
	.cfi_def_cfa_offset 48
	popq	%rbx
	.cfi_def_cfa_offset 40
	popq	%rbp
	.cfi_def_cfa_offset 32
	popq	%r12
	.cfi_def_cfa_offset 24
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L126:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	ret
	.cfi_endproc
.LFE8843:
	.size	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0, .-_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0
	.align 2
	.p2align 4
	.type	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE8_M_eraseESt17integral_constantIbLb1EERKm.isra.0, @function
_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE8_M_eraseESt17integral_constantIbLb1EERKm.isra.0:
.LFB8844:
	.cfi_startproc
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	movq	%rsi, %rax
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	xorl	%edx, %edx
	subq	$8, %rsp
	.cfi_def_cfa_offset 48
	movq	8(%rdi), %r13
	movq	(%rdi), %rbp
	divq	%r13
	leaq	0(%rbp,%rdx,8), %r12
	movq	(%r12), %r9
	testq	%r9, %r9
	je	.L149
	movq	%rdi, %rbx
	movq	(%r9), %rdi
	movq	%rdx, %r11
	movq	%r9, %r10
	movq	8(%rdi), %rcx
	cmpq	%rcx, %rsi
	je	.L131
.L151:
	movq	(%rdi), %r8
	testq	%r8, %r8
	je	.L149
	movq	8(%r8), %rcx
	xorl	%edx, %edx
	movq	%rdi, %r10
	movq	%rcx, %rax
	divq	%r13
	cmpq	%rdx, %r11
	jne	.L149
	movq	%r8, %rdi
	cmpq	%rcx, %rsi
	jne	.L151
.L131:
	movq	(%rdi), %rcx
	cmpq	%r10, %r9
	je	.L152
	testq	%rcx, %rcx
	je	.L134
	movq	8(%rcx), %rax
	xorl	%edx, %edx
	divq	%r13
	cmpq	%rdx, %r11
	je	.L134
	movq	%r10, 0(%rbp,%rdx,8)
	movq	(%rdi), %rcx
.L134:
	movq	%rcx, (%r10)
	movl	$16, %esi
	call	_ZdlPvm@PLT
	decq	24(%rbx)
.L149:
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L152:
	.cfi_restore_state
	testq	%rcx, %rcx
	je	.L138
	movq	8(%rcx), %rax
	xorl	%edx, %edx
	divq	%r13
	cmpq	%rdx, %r11
	je	.L134
	movq	%r10, 0(%rbp,%rdx,8)
	movq	(%r12), %rax
.L133:
	leaq	16(%rbx), %rdx
	cmpq	%rdx, %rax
	je	.L153
.L135:
	movq	$0, (%r12)
	movq	(%rdi), %rcx
	jmp	.L134
	.p2align 4
	.p2align 3
.L138:
	movq	%r10, %rax
	jmp	.L133
	.p2align 4
	.p2align 3
.L153:
	movq	%rcx, 16(%rbx)
	jmp	.L135
	.cfi_endproc
.LFE8844:
	.size	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE8_M_eraseESt17integral_constantIbLb1EERKm.isra.0, .-_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE8_M_eraseESt17integral_constantIbLb1EERKm.isra.0
	.p2align 4
	.type	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0, @function
_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0:
.LFB8845:
	.cfi_startproc
	leaq	-1(%rdx), %rax
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	pushq	%rbp
	.cfi_def_cfa_offset 24
	.cfi_offset 6, -24
	movq	%rdx, %rbp
	movq	%rax, %r11
	pushq	%rbx
	.cfi_def_cfa_offset 32
	.cfi_offset 3, -32
	movq	%rdi, %r8
	movq	%rsi, %r9
	shrq	$63, %r11
	movq	%rdx, %r10
	vmovsd	%xmm0, %xmm0, %xmm2
	andl	$1, %ebp
	addq	%rax, %r11
	sarq	%r11
	cmpq	%r11, %rsi
	jge	.L155
	movq	%rsi, %rdi
	jmp	.L161
	.p2align 4
	.p2align 3
.L156:
	movq	8(%rax), %r14
	cmpq	%r14, 8(%rsi)
	jnb	.L159
.L158:
	vmovdqu	(%rax), %xmm3
	salq	$4, %rdi
	vmovdqu	%xmm3, (%r8,%rdi)
	cmpq	%r11, %rdx
	jge	.L160
.L168:
	movq	%rdx, %rdi
.L161:
	leaq	1(%rdi), %rsi
	leaq	(%rsi,%rsi), %rbx
	salq	$5, %rsi
	leaq	-1(%rbx), %rdx
	addq	%r8, %rsi
	movq	%rdx, %rax
	vmovsd	(%rsi), %xmm0
	salq	$4, %rax
	addq	%r8, %rax
	vmovsd	(%rax), %xmm1
	vucomisd	%xmm1, %xmm0
	jp	.L173
	je	.L156
.L173:
	vcomisd	%xmm0, %xmm1
	ja	.L158
.L159:
	vmovdqu	(%rsi), %xmm4
	salq	$4, %rdi
	vmovdqu	%xmm4, (%r8,%rdi)
	cmpq	%r11, %rbx
	jge	.L179
	movq	%rbx, %rdx
	jmp	.L168
.L179:
	movq	%rsi, %rax
	movq	%rbx, %rdx
.L160:
	testq	%rbp, %rbp
	je	.L169
.L162:
	leaq	-1(%rdx), %rsi
	movq	%rsi, %rdi
	shrq	$63, %rdi
	addq	%rsi, %rdi
	sarq	%rdi
	cmpq	%r9, %rdx
	jg	.L167
	jmp	.L163
	.p2align 4
	.p2align 3
.L164:
	cmpq	%rcx, 8(%rax)
	jnb	.L178
.L166:
	vmovdqu	(%rax), %xmm5
	salq	$4, %rdx
	leaq	-1(%rdi), %rsi
	vmovdqu	%xmm5, (%r8,%rdx)
	movq	%rsi, %rdx
	shrq	$63, %rdx
	addq	%rdx, %rsi
	movq	%rdi, %rdx
	sarq	%rsi
	cmpq	%rdi, %r9
	jge	.L163
	movq	%rsi, %rdi
.L167:
	movq	%rdi, %rax
	salq	$4, %rax
	addq	%r8, %rax
	vmovsd	(%rax), %xmm0
	vucomisd	%xmm2, %xmm0
	jp	.L174
	je	.L164
.L174:
	vcomisd	%xmm0, %xmm2
	ja	.L166
.L178:
	salq	$4, %rdx
	leaq	(%r8,%rdx), %rax
.L163:
	vmovsd	%xmm2, (%rax)
	movq	%rcx, 8(%rax)
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L155:
	.cfi_restore_state
	movq	%rsi, %rax
	salq	$4, %rax
	addq	%rdi, %rax
	testq	%rbp, %rbp
	jne	.L163
	movq	%r9, %rdx
	.p2align 4
	.p2align 3
.L169:
	subq	$2, %r10
	movq	%r10, %rsi
	shrq	$63, %rsi
	addq	%r10, %rsi
	sarq	%rsi
	cmpq	%rdx, %rsi
	jne	.L162
	leaq	1(%rdx,%rdx), %rdx
	movq	%rdx, %rsi
	salq	$4, %rsi
	addq	%r8, %rsi
	vmovdqu	(%rsi), %xmm6
	vmovdqu	%xmm6, (%rax)
	movq	%rsi, %rax
	jmp	.L162
	.cfi_endproc
.LFE8845:
	.size	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0, .-_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	.section	.text._ZSt8pop_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEESt4lessIS2_EEvT_SA_T0_.constprop.0,"axG",@progbits,_ZN9Optimizer3runEv,comdat
	.p2align 4
	.type	_ZSt8pop_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEESt4lessIS2_EEvT_SA_T0_.constprop.0, @function
_ZSt8pop_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEESt4lessIS2_EEvT_SA_T0_.constprop.0:
.LFB8847:
	.cfi_startproc
	movq	%rsi, %rax
	subq	%rdi, %rax
	cmpq	$16, %rax
	jg	.L183
	ret
	.p2align 4
	.p2align 3
.L183:
	vmovdqu	(%rdi), %xmm1
	movq	-16(%rsi), %rax
	leaq	-16(%rsi), %rdx
	movq	-8(%rsi), %rcx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovq	%rax, %xmm0
	vmovdqu	%xmm1, -16(%rsi)
	xorl	%esi, %esi
	jmp	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	.cfi_endproc
.LFE8847:
	.size	_ZSt8pop_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEESt4lessIS2_EEvT_SA_T0_.constprop.0, .-_ZSt8pop_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEESt4lessIS2_EEvT_SA_T0_.constprop.0
	.text
	.align 2
	.p2align 4
	.type	_ZNSt6vectorIiSaIiEEaSERKS1_.isra.0, @function
_ZNSt6vectorIiSaIiEEaSERKS1_.isra.0:
.LFB8849:
	.cfi_startproc
	cmpq	%rdi, %rsi
	je	.L206
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	pushq	%r13
	.cfi_def_cfa_offset 24
	.cfi_offset 13, -24
	pushq	%r12
	.cfi_def_cfa_offset 32
	.cfi_offset 12, -32
	pushq	%rbp
	.cfi_def_cfa_offset 40
	.cfi_offset 6, -40
	pushq	%rbx
	.cfi_def_cfa_offset 48
	.cfi_offset 3, -48
	movq	%rdi, %rbx
	movq	%rsi, %rbp
	movq	8(%rsi), %r14
	movq	(%rsi), %r13
	movq	(%rdi), %rdi
	movq	16(%rbx), %rax
	movq	%r14, %r12
	subq	%r13, %r12
	subq	%rdi, %rax
	cmpq	%rax, %r12
	ja	.L210
	movq	8(%rbx), %r8
	movq	%r8, %rdx
	subq	%rdi, %rdx
	cmpq	%rdx, %r12
	ja	.L193
	cmpq	%r13, %r14
	je	.L209
	movq	%r12, %rdx
	movq	%r13, %rsi
	call	memmove@PLT
	addq	(%rbx), %r12
	movq	%r12, 8(%rbx)
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbp
	.cfi_def_cfa_offset 32
	popq	%r12
	.cfi_def_cfa_offset 24
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L210:
	.cfi_restore_state
	testq	%r12, %r12
	je	.L197
	movabsq	$9223372036854775804, %rax
	cmpq	%rax, %r12
	ja	.L211
	movq	%r12, %rdi
	call	_Znwm@PLT
	movq	%rax, %rbp
.L187:
	cmpq	%r13, %r14
	je	.L190
	movq	%r12, %rdx
	movq	%r13, %rsi
	movq	%rbp, %rdi
	call	memcpy@PLT
.L190:
	movq	(%rbx), %rdi
	testq	%rdi, %rdi
	je	.L191
	movq	16(%rbx), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L191:
	addq	%rbp, %r12
	movq	%rbp, (%rbx)
	movq	%r12, 16(%rbx)
	movq	%r12, 8(%rbx)
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbp
	.cfi_def_cfa_offset 32
	popq	%r12
	.cfi_def_cfa_offset 24
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L193:
	.cfi_restore_state
	testq	%rdx, %rdx
	je	.L195
	movq	%r13, %rsi
	call	memmove@PLT
	movq	8(%rbx), %r8
	movq	(%rbx), %rdi
	movq	8(%rbp), %r14
	movq	0(%rbp), %r13
	movq	%r8, %rdx
	subq	%rdi, %rdx
.L195:
	leaq	0(%r13,%rdx), %rsi
	cmpq	%r14, %rsi
	jne	.L196
.L209:
	addq	%rdi, %r12
	movq	%r12, 8(%rbx)
	popq	%rbx
	.cfi_def_cfa_offset 40
	popq	%rbp
	.cfi_def_cfa_offset 32
	popq	%r12
	.cfi_def_cfa_offset 24
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L206:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	ret
	.p2align 4
	.p2align 3
.L196:
	.cfi_def_cfa_offset 48
	.cfi_offset 3, -48
	.cfi_offset 6, -40
	.cfi_offset 12, -32
	.cfi_offset 13, -24
	.cfi_offset 14, -16
	movq	%r14, %rdx
	movq	%r8, %rdi
	subq	%rsi, %rdx
	call	memmove@PLT
	addq	(%rbx), %r12
	movq	%r12, 8(%rbx)
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbp
	.cfi_def_cfa_offset 32
	popq	%r12
	.cfi_def_cfa_offset 24
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L197:
	.cfi_restore_state
	xorl	%ebp, %ebp
	jmp	.L187
	.p2align 4
	.p2align 3
.L211:
	testq	%r12, %r12
	jns	.L189
	call	_ZSt28__throw_bad_array_new_lengthv@PLT
.L189:
	call	_ZSt17__throw_bad_allocv@PLT
	.cfi_endproc
.LFE8849:
	.size	_ZNSt6vectorIiSaIiEEaSERKS1_.isra.0, .-_ZNSt6vectorIiSaIiEEaSERKS1_.isra.0
	.section	.text._ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_less_iterEEvT_SB_T0_T1_.isra.0,"axG",@progbits,_ZN9Optimizer14informed_seedsEv,comdat
	.p2align 4
	.type	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_less_iterEEvT_SB_T0_T1_.isra.0, @function
_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_less_iterEEvT_SB_T0_T1_.isra.0:
.LFB8852:
	.cfi_startproc
	movq	%rsi, %rax
	subq	%rdi, %rax
	cmpq	$256, %rax
	jle	.L262
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	movq	%rdx, %r14
	pushq	%r13
	.cfi_def_cfa_offset 24
	.cfi_offset 13, -24
	movq	%rsi, %r13
	pushq	%r12
	.cfi_def_cfa_offset 32
	.cfi_offset 12, -32
	movq	%rdi, %r12
	pushq	%rbp
	.cfi_def_cfa_offset 40
	.cfi_offset 6, -40
	leaq	16(%rdi), %rbp
	pushq	%rbx
	.cfi_def_cfa_offset 48
	.cfi_offset 3, -48
	testq	%rdx, %rdx
	je	.L215
.L216:
	movq	%rsi, %rax
	vmovsd	16(%r12), %xmm0
	decq	%r14
	subq	%r12, %rax
	movq	%rax, %rdx
	shrq	$63, %rax
	sarq	$4, %rdx
	addq	%rdx, %rax
	sarq	%rax
	salq	$4, %rax
	addq	%r12, %rax
	vmovsd	(%rax), %xmm1
	vcomisd	%xmm0, %xmm1
	ja	.L221
	vcomisd	%xmm1, %xmm0
	ja	.L222
	movl	8(%rax), %ecx
	cmpl	%ecx, 24(%r12)
	jl	.L221
.L222:
	vmovsd	-16(%rsi), %xmm2
	vcomisd	%xmm0, %xmm2
	jbe	.L263
	movl	24(%r12), %edx
.L234:
	vmovsd	(%r12), %xmm1
	movl	8(%r12), %eax
	vmovsd	%xmm0, (%r12)
	movl	%edx, 8(%r12)
	movl	%eax, 24(%r12)
	vmovsd	%xmm1, 16(%r12)
.L230:
	movq	%rsi, %rdx
	movq	%rbp, %rbx
	.p2align 4
	.p2align 3
.L239:
	vmovsd	(%rbx), %xmm1
	movq	%rbx, %r13
	vcomisd	%xmm1, %xmm0
	ja	.L240
	vcomisd	%xmm0, %xmm1
	ja	.L241
	movl	8(%r12), %eax
	cmpl	%eax, 8(%rbx)
	jl	.L240
.L241:
	leaq	-16(%rdx), %rax
.L242:
	vmovsd	(%rax), %xmm2
	movq	%rax, %rdx
	vcomisd	%xmm0, %xmm2
	ja	.L243
	vcomisd	%xmm2, %xmm0
	ja	.L244
	movl	8(%rax), %edi
	cmpl	%edi, 8(%r12)
	jl	.L243
.L244:
	cmpq	%rax, %rbx
	jnb	.L264
	movl	8(%rbx), %ecx
	movl	8(%rax), %edi
	vmovsd	%xmm2, (%rbx)
	vmovsd	%xmm1, (%rax)
	addq	$16, %rbx
	vmovsd	(%r12), %xmm0
	movl	%edi, -8(%rbx)
	movl	%ecx, 8(%rax)
	jmp	.L239
	.p2align 4
	.p2align 3
.L221:
	vmovsd	-16(%rsi), %xmm2
	vcomisd	%xmm1, %xmm2
	ja	.L225
	vcomisd	%xmm2, %xmm1
	ja	.L226
	movl	8(%rax), %edx
	cmpl	-8(%rsi), %edx
	jge	.L226
	.p2align 4
	.p2align 3
.L227:
	vmovsd	(%r12), %xmm0
	movl	8(%r12), %ecx
	vmovsd	%xmm1, (%r12)
	vmovsd	%xmm0, (%rax)
	movl	%edx, 8(%r12)
	vmovsd	(%r12), %xmm0
	movl	%ecx, 8(%rax)
	jmp	.L230
.L226:
	vcomisd	%xmm0, %xmm2
	jbe	.L265
	movl	-8(%rsi), %eax
.L232:
	vmovsd	(%r12), %xmm0
	movl	8(%r12), %edx
	vmovsd	%xmm2, (%r12)
	vmovsd	%xmm0, -16(%rsi)
	movl	%eax, 8(%r12)
	vmovsd	(%r12), %xmm0
	movl	%edx, -8(%rsi)
	jmp	.L230
	.p2align 4
	.p2align 3
.L243:
	subq	$16, %rax
	jmp	.L242
	.p2align 4
	.p2align 3
.L240:
	addq	$16, %rbx
	jmp	.L239
	.p2align 4
	.p2align 3
.L264:
	movq	%r14, %rdx
	movq	%rbx, %rdi
	call	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_less_iterEEvT_SB_T0_T1_.isra.0
	movq	%rbx, %rax
	subq	%r12, %rax
	cmpq	$256, %rax
	jle	.L258
	testq	%r14, %r14
	je	.L215
	movq	%rbx, %rsi
	jmp	.L216
	.p2align 4
	.p2align 3
.L225:
	movl	8(%rax), %edx
	jmp	.L227
.L215:
	sarq	$4, %rax
	leaq	-2(%rax), %r14
	movq	%rax, %rbx
	sarq	%r14
	movq	%r14, %rbp
	salq	$4, %rbp
	addq	%r12, %rbp
	jmp	.L219
	.p2align 4
	.p2align 3
.L217:
	decq	%r14
.L219:
	vmovsd	0(%rbp), %xmm0
	movl	8(%rbp), %ecx
	movq	%rbx, %rdx
	movq	%r14, %rsi
	movq	%r12, %rdi
	subq	$16, %rbp
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_less_iterEEvT_T0_SC_T1_T2_.isra.0
	testq	%r14, %r14
	jne	.L217
	subq	$16, %r13
	.p2align 4
	.p2align 3
.L218:
	vmovsd	(%r12), %xmm1
	vmovsd	0(%r13), %xmm0
	movq	%r13, %rbx
	xorl	%esi, %esi
	movl	8(%r12), %eax
	movl	8(%r13), %ecx
	subq	%r12, %rbx
	movq	%r12, %rdi
	movq	%rbx, %rdx
	subq	$16, %r13
	sarq	$4, %rdx
	movl	%eax, 24(%r13)
	vmovsd	%xmm1, 16(%r13)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_less_iterEEvT_T0_SC_T1_T2_.isra.0
	cmpq	$16, %rbx
	jg	.L218
.L258:
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbp
	.cfi_def_cfa_offset 32
	popq	%r12
	.cfi_def_cfa_offset 24
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
.L263:
	.cfi_restore_state
	vcomisd	%xmm2, %xmm0
	ja	.L233
	movl	24(%r12), %edx
	cmpl	-8(%rsi), %edx
	jl	.L234
.L233:
	vcomisd	%xmm1, %xmm2
	jbe	.L266
	movl	-8(%rsi), %edx
.L238:
	vmovsd	(%r12), %xmm0
	movl	8(%r12), %eax
	vmovsd	%xmm2, (%r12)
	vmovsd	%xmm0, -16(%rsi)
	movl	%edx, 8(%r12)
	vmovsd	(%r12), %xmm0
	movl	%eax, -8(%rsi)
	jmp	.L230
.L265:
	movl	24(%r12), %edx
	vcomisd	%xmm2, %xmm0
	ja	.L234
	movl	-8(%rsi), %eax
	cmpl	%edx, %eax
	jg	.L232
	jmp	.L234
.L266:
	movl	8(%rax), %ecx
	vcomisd	%xmm2, %xmm1
	ja	.L237
	movl	-8(%rsi), %edx
	cmpl	%ecx, %edx
	jg	.L238
.L237:
	vmovsd	(%r12), %xmm0
	movl	8(%r12), %edx
	vmovsd	%xmm1, (%r12)
	vmovsd	%xmm0, (%rax)
	movl	%ecx, 8(%r12)
	vmovsd	(%r12), %xmm0
	movl	%edx, 8(%rax)
	jmp	.L230
.L262:
	.cfi_def_cfa_offset 8
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	ret
	.cfi_endproc
.LFE8852:
	.size	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_less_iterEEvT_SB_T0_T1_.isra.0, .-_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_less_iterEEvT_SB_T0_T1_.isra.0
	.section	.text._ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_less_iterEEvT_SB_T0_.isra.0,"axG",@progbits,_ZN9Optimizer14informed_seedsEv,comdat
	.p2align 4
	.type	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_less_iterEEvT_SB_T0_.isra.0, @function
_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_less_iterEEvT_SB_T0_.isra.0:
.LFB8858:
	.cfi_startproc
	movq	%rsi, %r11
	cmpq	%rsi, %rdi
	je	.L284
	leaq	16(%rdi), %rsi
	cmpq	%rsi, %r11
	je	.L284
	leaq	32(%rdi), %r8
	.p2align 4
	.p2align 3
.L279:
	vmovsd	(%rsi), %xmm1
	vmovsd	(%rdi), %xmm0
	movq	%rsi, %rax
	movl	8(%rsi), %r9d
	vcomisd	%xmm1, %xmm0
	ja	.L270
	vcomisd	%xmm0, %xmm1
	ja	.L272
	cmpl	%r9d, 8(%rdi)
	jle	.L272
.L270:
	movq	%rsi, %rcx
	movq	%r8, %r10
	subq	%rdi, %rcx
	movq	%rcx, %rdx
	sarq	$4, %rdx
	testq	%rcx, %rcx
	jle	.L278
	.p2align 4
	.p2align 3
.L277:
	vmovsd	-16(%rax), %xmm0
	movl	-8(%rax), %ecx
	subq	$16, %rax
	decq	%rdx
	movl	%ecx, 24(%rax)
	vmovsd	%xmm0, 16(%rax)
	jne	.L277
.L278:
	vmovsd	%xmm1, (%rdi)
	movl	%r9d, 8(%rdi)
	addq	$16, %rsi
	addq	$16, %r8
	cmpq	%r10, %r11
	jne	.L279
.L284:
	ret
	.p2align 4
	.p2align 3
.L273:
	movl	-8(%rax), %edx
.L275:
	vmovsd	%xmm0, (%rax)
	movl	%edx, 8(%rax)
	subq	$16, %rax
.L272:
	vmovsd	-16(%rax), %xmm0
	vcomisd	%xmm1, %xmm0
	ja	.L273
	vcomisd	%xmm0, %xmm1
	ja	.L274
	movl	-8(%rax), %edx
	cmpl	%r9d, %edx
	jg	.L275
.L274:
	movq	%r8, %r10
	vmovsd	%xmm1, (%rax)
	movl	%r9d, 8(%rax)
	addq	$16, %rsi
	addq	$16, %r8
	cmpq	%r10, %r11
	jne	.L279
	ret
	.cfi_endproc
.LFE8858:
	.size	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_less_iterEEvT_SB_T0_.isra.0, .-_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_less_iterEEvT_SB_T0_.isra.0
	.section	.rodata.str1.1,"aMS",@progbits,1
.LC0:
	.string	"vector::_M_realloc_insert"
	.text
	.align 2
	.p2align 4
	.type	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0, @function
_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0:
.LFB8860:
	.cfi_startproc
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	%rdi, %rbx
	subq	$24, %rsp
	.cfi_def_cfa_offset 64
	movq	8(%rdi), %r12
	cmpq	16(%rdi), %r12
	je	.L286
	vmovdqu	(%rsi), %xmm2
	addq	$16, %r12
	vmovdqu	%xmm2, -16(%r12)
	movq	%r12, 8(%rdi)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L286:
	.cfi_restore_state
	movq	(%rdi), %r13
	movabsq	$576460752303423487, %rax
	subq	%r13, %r12
	movq	%r12, %rdx
	sarq	$4, %rdx
	cmpq	%rax, %rdx
	je	.L304
	testq	%rdx, %rdx
	movl	$1, %eax
	cmovne	%rdx, %rax
	addq	%rdx, %rax
	jc	.L290
	testq	%rax, %rax
	jne	.L305
	xorl	%ebp, %ebp
	xorl	%edi, %edi
.L292:
	vmovdqu	(%rsi), %xmm3
	leaq	16(%rdi,%r12), %rax
	vmovq	%rdi, %xmm1
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqu	%xmm3, (%rdi,%r12)
	testq	%r12, %r12
	jg	.L306
	testq	%r13, %r13
	jne	.L307
.L295:
	movq	%rbp, 16(%rbx)
	vmovdqu	%xmm0, (%rbx)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L306:
	.cfi_restore_state
	movq	%r13, %rsi
	movq	%r12, %rdx
	vmovdqa	%xmm0, (%rsp)
	call	memmove@PLT
	vmovdqa	(%rsp), %xmm0
	movq	16(%rbx), %rsi
	subq	%r13, %rsi
.L294:
	movq	%r13, %rdi
	vmovdqa	%xmm0, (%rsp)
	call	_ZdlPvm@PLT
	vmovdqa	(%rsp), %xmm0
	jmp	.L295
	.p2align 4
	.p2align 3
.L307:
	movq	16(%rbx), %rsi
	subq	%r13, %rsi
	jmp	.L294
.L305:
	movabsq	$576460752303423487, %rbp
	cmpq	%rbp, %rax
	cmovbe	%rax, %rbp
	salq	$4, %rbp
.L291:
	movq	%rbp, %rdi
	movq	%rsi, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rsi
	addq	%rax, %rbp
	jmp	.L292
.L290:
	movabsq	$9223372036854775792, %rbp
	jmp	.L291
.L304:
	leaq	.LC0(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE8860:
	.size	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0, .-_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	.section	.text._ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_.isra.0,"axG",@progbits,_ZN11TableSearch5solveERK12TableProblemid,comdat
	.p2align 4
	.type	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_.isra.0, @function
_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_.isra.0:
.LFB8861:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	andq	$-32, %rsp
	addq	$-128, %rsp
	.cfi_offset 14, -24
	.cfi_offset 13, -32
	.cfi_offset 12, -40
	.cfi_offset 3, -48
	movq	%fs:40, %rax
	movq	%rax, 120(%rsp)
	xorl	%eax, %eax
	cmpq	%rsi, %rdi
	je	.L308
	leaq	96(%rdi), %rbx
	movq	%rdi, %r12
	movq	%rsi, %r14
	cmpq	%rbx, %rsi
	je	.L308
	movl	$96, %r13d
	jmp	.L317
	.p2align 4
	.p2align 3
.L327:
	vmovdqa	(%rbx), %xmm7
	vmovdqa	64(%rbx), %xmm0
	vmovdqa	80(%rbx), %xmm1
	vmovdqa	%xmm7, (%rsp)
	vmovdqa	16(%rbx), %xmm7
	vmovdqa	%xmm0, 64(%rsp)
	vmovdqa	%xmm1, 80(%rsp)
	vmovdqa	%xmm7, 16(%rsp)
	vmovdqa	32(%rbx), %xmm7
	vmovdqa	%xmm7, 32(%rsp)
	vmovdqa	48(%rbx), %xmm7
	vmovdqa	%xmm7, 48(%rsp)
	cmpq	%rbx, %r12
	je	.L312
	subq	%r12, %rdx
	leaq	(%r12,%r13), %rdi
	movq	%r12, %rsi
	call	memmove@PLT
.L312:
	vmovdqa	(%rsp), %xmm2
	vmovdqa	16(%rsp), %xmm3
	addq	$96, %rbx
	vmovdqa	32(%rsp), %xmm4
	vmovdqa	48(%rsp), %xmm5
	vmovdqa	64(%rsp), %xmm6
	vmovdqa	80(%rsp), %xmm7
	vmovdqa	%xmm2, (%r12)
	vmovdqa	%xmm3, 16(%r12)
	vmovdqa	%xmm4, 32(%r12)
	vmovdqa	%xmm5, 48(%r12)
	vmovdqa	%xmm6, 64(%r12)
	vmovdqa	%xmm7, 80(%r12)
	cmpq	%rbx, %r14
	je	.L308
.L317:
	movq	%rbx, %rdx
	vmovsd	16(%rbx), %xmm0
	vcomisd	16(%r12), %xmm0
	ja	.L327
	vmovdqa	(%rbx), %xmm1
	vmovdqa	16(%rbx), %xmm2
	leaq	-96(%rbx), %rax
	vmovdqa	32(%rbx), %xmm3
	vmovdqa	48(%rbx), %xmm4
	vmovdqa	64(%rbx), %xmm5
	vmovdqa	80(%rbx), %xmm6
	vcomisd	-80(%rbx), %xmm0
	vmovdqa	%xmm1, (%rsp)
	vmovdqa	%xmm2, 16(%rsp)
	vmovdqa	%xmm3, 32(%rsp)
	vmovdqa	%xmm4, 48(%rsp)
	vmovdqa	%xmm5, 64(%rsp)
	vmovdqa	%xmm6, 80(%rsp)
	jbe	.L314
	.p2align 4
	.p2align 3
.L316:
	vmovdqa	(%rax), %xmm1
	vmovdqa	16(%rax), %xmm2
	movq	%rax, %rdx
	subq	$96, %rax
	vmovdqa	128(%rax), %xmm3
	vmovdqa	144(%rax), %xmm4
	vmovdqa	160(%rax), %xmm5
	vmovdqa	176(%rax), %xmm6
	vmovdqa	%xmm1, 192(%rax)
	vmovdqa	%xmm2, 208(%rax)
	vmovdqa	%xmm3, 224(%rax)
	vmovdqa	%xmm4, 240(%rax)
	vmovdqa	%xmm5, 256(%rax)
	vmovdqa	%xmm6, 272(%rax)
	vcomisd	16(%rax), %xmm0
	ja	.L316
.L314:
	vmovdqa	(%rsp), %xmm0
	vmovdqa	16(%rsp), %xmm7
	addq	$96, %rbx
	vmovdqa	48(%rsp), %xmm1
	vmovdqa	64(%rsp), %xmm2
	vmovdqa	80(%rsp), %xmm3
	vmovdqa	%xmm0, (%rdx)
	vmovdqa	32(%rsp), %xmm0
	vmovdqa	%xmm7, 16(%rdx)
	vmovdqa	%xmm1, 48(%rdx)
	vmovdqa	%xmm2, 64(%rdx)
	vmovdqa	%xmm3, 80(%rdx)
	vmovdqa	%xmm0, 32(%rdx)
	cmpq	%rbx, %r14
	jne	.L317
.L308:
	movq	120(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L328
	leaq	-32(%rbp), %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
.L328:
	.cfi_restore_state
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE8861:
	.size	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_.isra.0, .-_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_.isra.0
	.section	.text._ZN9Optimizer12distributionEmP6Values,"axG",@progbits,_ZN9Optimizer12distributionEmP6Values,comdat
	.align 2
	.p2align 4
	.weak	_ZN9Optimizer12distributionEmP6Values
	.type	_ZN9Optimizer12distributionEmP6Values, @function
_ZN9Optimizer12distributionEmP6Values:
.LFB5997:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	.cfi_offset 15, -24
	.cfi_offset 14, -32
	.cfi_offset 13, -40
	.cfi_offset 12, -48
	.cfi_offset 3, -56
	movq	%rdi, %r12
	movq	%rsi, %r13
	andq	$-64, %rsp
	movq	%rdx, %rbx
	xorl	%esi, %esi
	movl	$512, %edx
	subq	$576, %rsp
	movq	%rsp, %r10
	movq	%r10, %rdi
	movq	%fs:40, %rax
	movq	%rax, 568(%rsp)
	xorl	%eax, %eax
	call	memset@PLT
	movq	%rax, %r10
	testq	%r13, %r13
	je	.L354
	movq	24(%r12), %r11
	movl	$1, %r8d
	leaq	4(%rsp), %r9
	jmp	.L338
.L393:
	vpbroadcastd	%edx, %zmm0
	vpxord	(%rsp), %zmm0, %zmm1
	movl	%r8d, %esi
	movslq	%r8d, %rcx
	leaq	(%r10,%rcx,4), %rax
	shrl	$4, %esi
	vmovdqu32	%zmm1, (%rax)
	cmpl	$1, %esi
	je	.L332
	vpxord	64(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 64(%rax)
	cmpl	$2, %esi
	je	.L332
	vpxord	128(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 128(%rax)
	cmpl	$3, %esi
	je	.L332
	vpxord	192(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 192(%rax)
	cmpl	$4, %esi
	je	.L332
	vpxord	256(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 256(%rax)
	cmpl	$5, %esi
	je	.L332
	vpxord	320(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 320(%rax)
	cmpl	$6, %esi
	je	.L332
	vpxord	384(%rsp), %zmm0, %zmm0
	vmovdqu32	%zmm0, 384(%rax)
.L332:
	movl	%r8d, %eax
	andl	$-16, %eax
	testb	$15, %r8b
	je	.L337
	movl	%r8d, %esi
	subl	%eax, %esi
	leal	-1(%rsi), %edi
	cmpl	$6, %edi
	jbe	.L334
	movl	%eax, %edi
	vpbroadcastd	%edx, %ymm0
	vpxor	(%rsp,%rdi,4), %ymm0, %ymm0
	addq	%rdi, %rcx
	vmovdqu	%ymm0, (%rsp,%rcx,4)
	movl	%esi, %ecx
	andl	$-8, %ecx
	addl	%ecx, %eax
	cmpl	%esi, %ecx
	je	.L337
.L334:
	movslq	%eax, %rsi
	leal	(%r8,%rax), %ecx
	movl	(%rsp,%rsi,4), %edi
	movslq	%ecx, %rcx
	xorl	%edx, %edi
	movl	%edi, (%rsp,%rcx,4)
	leal	1(%rax), %ecx
	cmpl	%ecx, %r8d
	jle	.L337
	leal	(%r8,%rcx), %esi
	movslq	%ecx, %rcx
	movl	(%rsp,%rcx,4), %edi
	movslq	%esi, %rsi
	leal	2(%rax), %ecx
	xorl	%edx, %edi
	movl	%edi, (%rsp,%rsi,4)
	cmpl	%ecx, %r8d
	jle	.L337
	leal	(%r8,%rcx), %esi
	movslq	%ecx, %rcx
	movl	(%rsp,%rcx,4), %edi
	movslq	%esi, %rsi
	leal	3(%rax), %ecx
	xorl	%edx, %edi
	movl	%edi, (%rsp,%rsi,4)
	cmpl	%r8d, %ecx
	jge	.L337
	leal	(%rcx,%r8), %esi
	movslq	%ecx, %rcx
	movl	(%rsp,%rcx,4), %edi
	movslq	%esi, %rsi
	leal	4(%rax), %ecx
	xorl	%edx, %edi
	movl	%edi, (%rsp,%rsi,4)
	cmpl	%ecx, %r8d
	jle	.L337
	leal	(%r8,%rcx), %esi
	movslq	%ecx, %rcx
	movl	(%rsp,%rcx,4), %edi
	movslq	%esi, %rsi
	leal	5(%rax), %ecx
	xorl	%edx, %edi
	movl	%edi, (%rsp,%rsi,4)
	cmpl	%r8d, %ecx
	jge	.L337
	leal	(%rcx,%r8), %esi
	movslq	%ecx, %rcx
	addl	$6, %eax
	movl	(%rsp,%rcx,4), %edi
	movslq	%esi, %rsi
	xorl	%edx, %edi
	movl	%edi, (%rsp,%rsi,4)
	cmpl	%eax, %r8d
	jle	.L337
	leal	(%r8,%rax), %ecx
	cltq
	xorl	(%rsp,%rax,4), %edx
	movslq	%ecx, %rcx
	movl	%edx, (%rsp,%rcx,4)
.L337:
	addl	%r8d, %r8d
	blsr	%r13, %r13
	je	.L392
.L338:
	tzcntq	%r13, %rax
	leal	-1(%r8), %ecx
	movl	(%r11,%rax,4), %edx
	cmpl	$14, %ecx
	ja	.L393
	leaq	(%r9,%rcx,4), %rdi
	movq	%r10, %rax
	movslq	%r8d, %rcx
.L336:
	movl	(%rax), %esi
	xorl	%edx, %esi
	movl	%esi, (%rax,%rcx,4)
	addq	$4, %rax
	cmpq	%rax, %rdi
	jne	.L336
	addl	%r8d, %r8d
	blsr	%r13, %r13
	jne	.L338
.L392:
	vmovsd	.LC1(%rip), %xmm10
	vxorps	%xmm4, %xmm4, %xmm4
	vcvtsi2sdl	%r8d, %xmm4, %xmm4
	vdivsd	%xmm4, %xmm10, %xmm4
.L330:
	vmovq	72(%r12), %xmm14
	vmovq	96(%r12), %xmm13
	leal	-1(%r8), %r13d
	movq	%rbx, %r11
	vbroadcastsd	.LC1(%rip), %zmm9
	leaq	(%r9,%r13,4), %rax
	movq	%rbx, %r14
	vmovq	%rax, %xmm12
	movl	$32, %eax
	vmovd	%eax, %xmm11
.L346:
	movl	(%r10), %r9d
	movl	2800(%r12), %edx
	movl	%r9d, %r15d
	cmpl	%edx, (%r12)
	jle	.L339
	imull	$-1640531535, %r9d, %r15d
	vmovd	%xmm11, %eax
	subl	%edx, %eax
	shrx	%eax, %r15d, %r15d
.L339:
	vmovq	%xmm14, %rax
	vmovq	%xmm13, %rdi
	leaq	(%rax,%r15,4), %rax
	salq	$6, %r15
	addq	%rdi, %r15
	cmpl	(%rax), %r9d
	je	.L340
	movq	48(%r12), %rdx
	movq	56(%r12), %rdi
	incq	2816(%r12)
	movl	%r9d, (%rax)
	cmpq	%rdi, %rdx
	je	.L356
	vmovsd	%xmm10, %xmm10, %xmm3
	vmovsd	%xmm10, %xmm10, %xmm8
	vmovsd	%xmm10, %xmm10, %xmm7
	vmovsd	%xmm10, %xmm10, %xmm1
	vmovsd	%xmm10, %xmm10, %xmm2
	vmovsd	%xmm10, %xmm10, %xmm6
	vmovsd	%xmm10, %xmm10, %xmm5
	vmovsd	%xmm10, %xmm10, %xmm0
.L342:
	movl	(%rdx), %esi
	xorl	%eax, %eax
	testl	%esi, %esi
	jle	.L345
	movl	4(%rdx), %eax
	andl	%r9d, %eax
	popcntl	%eax, %eax
	andl	$1, %eax
	cmpl	$1, %esi
	je	.L345
	movl	8(%rdx), %ecx
	andl	%r9d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	addl	%ecx, %ecx
	orl	%ecx, %eax
	cmpl	$2, %esi
	je	.L345
	movl	12(%rdx), %ecx
	andl	%r9d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	sall	$2, %ecx
	orl	%ecx, %eax
.L345:
	cltq
	movq	%rax, %rcx
	salq	$6, %rcx
	vmulsd	224(%rcx,%rdx), %xmm0, %xmm0
	vmulsd	232(%rdx,%rcx), %xmm5, %xmm5
	addq	$736, %rdx
	vmulsd	-496(%rdx,%rcx), %xmm6, %xmm6
	vmulsd	-488(%rdx,%rcx), %xmm2, %xmm2
	vmulsd	-480(%rdx,%rcx), %xmm1, %xmm1
	vmulsd	-472(%rdx,%rcx), %xmm7, %xmm7
	vmulsd	-464(%rdx,%rcx), %xmm8, %xmm8
	vmulsd	-456(%rdx,%rcx), %xmm3, %xmm3
	cmpq	%rdx, %rdi
	jne	.L342
	vunpcklpd	%xmm3, %xmm8, %xmm3
	vunpcklpd	%xmm7, %xmm1, %xmm1
	vunpcklpd	%xmm2, %xmm6, %xmm2
	vunpcklpd	%xmm5, %xmm0, %xmm0
	vinsertf128	$0x1, %xmm3, %ymm1, %ymm1
	vinsertf128	$0x1, %xmm2, %ymm0, %ymm0
	vinsertf64x4	$0x1, %ymm1, %zmm0, %zmm0
.L341:
	vmovupd	%zmm0, (%r15)
.L340:
	vmovdqa	(%r15), %xmm5
	addq	$4, %r10
	vmovq	%xmm12, %rax
	addq	$64, %r14
	vmovdqa	%xmm5, -64(%r14)
	vmovdqa	16(%r15), %xmm6
	vmovdqa	%xmm6, -48(%r14)
	vmovdqa	32(%r15), %xmm7
	vmovdqa	%xmm7, -32(%r14)
	vmovdqa	48(%r15), %xmm3
	vmovdqa	%xmm3, -16(%r14)
	cmpq	%rax, %r10
	jne	.L346
	movl	$1, %r10d
	cmpl	$1, %r8d
	je	.L348
.L347:
	movslq	%r10d, %rsi
	addl	%r10d, %r10d
	movq	%rbx, %rdx
	xorl	%edi, %edi
	movslq	%r10d, %r9
	salq	$6, %rsi
	salq	$6, %r9
	leaq	(%rbx,%rsi), %rcx
	.p2align 4
	.p2align 3
.L351:
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L349:
	vmovupd	(%rdx,%rax), %zmm0
	vmovupd	(%rcx,%rax), %zmm1
	vaddpd	%zmm0, %zmm1, %zmm2
	vsubpd	%zmm1, %zmm0, %zmm0
	vmovupd	%zmm2, (%rdx,%rax)
	vmovupd	%zmm0, (%rcx,%rax)
	addq	$64, %rax
	cmpq	%rsi, %rax
	jne	.L349
	addl	%r10d, %edi
	addq	%r9, %rdx
	addq	%r9, %rcx
	cmpl	%edi, %r8d
	jg	.L351
	cmpl	%r8d, %r10d
	jl	.L347
.L348:
	salq	$6, %r13
	vbroadcastsd	%xmm4, %zmm4
	leaq	64(%rbx,%r13), %rax
.L352:
	vmulpd	(%r11), %zmm4, %zmm0
	addq	$64, %r11
	vmovupd	%zmm0, -64(%r11)
	cmpq	%rax, %r11
	jne	.L352
	movq	568(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L394
	movl	%r8d, %eax
	vzeroupper
	leaq	-40(%rbp), %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
.L356:
	.cfi_restore_state
	vmovapd	%zmm9, %zmm0
	jmp	.L341
.L354:
	vmovsd	.LC1(%rip), %xmm10
	movl	$1, %r8d
	leaq	4(%rsp), %r9
	vmovsd	%xmm10, %xmm10, %xmm4
	jmp	.L330
.L394:
	vzeroupper
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE5997:
	.size	_ZN9Optimizer12distributionEmP6Values, .-_ZN9Optimizer12distributionEmP6Values
	.section	.text._ZZN9Optimizer14informed_seedsEvENKUljE_clEj,"axG",@progbits,_ZZN9Optimizer14informed_seedsEvENKUljE_clEj,comdat
	.align 2
	.p2align 4
	.weak	_ZZN9Optimizer14informed_seedsEvENKUljE_clEj
	.type	_ZZN9Optimizer14informed_seedsEvENKUljE_clEj, @function
_ZZN9Optimizer14informed_seedsEvENKUljE_clEj:
.LFB6028:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movl	%esi, %r8d
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	.cfi_offset 15, -24
	.cfi_offset 14, -32
	.cfi_offset 13, -40
	.cfi_offset 12, -48
	.cfi_offset 3, -56
	movq	%rdi, %r15
	movl	%esi, %r14d
	andq	$-64, %rsp
	subq	$192, %rsp
	movq	(%rdi), %r9
	movq	%fs:40, %rax
	movq	%rax, 184(%rsp)
	xorl	%eax, %eax
	movl	2800(%r9), %eax
	cmpl	%eax, (%r9)
	jle	.L396
	imull	$-1640531535, %esi, %r8d
	movl	$32, %edx
	subl	%eax, %edx
	shrx	%edx, %r8d, %r8d
.L396:
	movq	72(%r9), %rax
	leaq	(%rax,%r8,4), %rax
	salq	$6, %r8
	addq	96(%r9), %r8
	cmpl	(%rax), %r14d
	je	.L397
	vbroadcastsd	.LC1(%rip), %zmm0
	movq	48(%r9), %rdx
	movq	56(%r9), %rsi
	incq	2816(%r9)
	movl	%r14d, (%rax)
	vmovapd	%zmm0, 64(%rsp)
	cmpq	%rsi, %rdx
	je	.L398
	.p2align 4
	.p2align 3
.L399:
	movl	(%rdx), %edi
	xorl	%eax, %eax
	testl	%edi, %edi
	jle	.L403
	movl	4(%rdx), %eax
	andl	%r14d, %eax
	popcntl	%eax, %eax
	andl	$1, %eax
	cmpl	$1, %edi
	je	.L403
	movl	8(%rdx), %ecx
	andl	%r14d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	addl	%ecx, %ecx
	orl	%ecx, %eax
	cmpl	$2, %edi
	je	.L403
	movl	12(%rdx), %ecx
	andl	%r14d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	sall	$2, %ecx
	orl	%ecx, %eax
.L403:
	cltq
	addq	$736, %rdx
	salq	$6, %rax
	vmulpd	-512(%rdx,%rax), %zmm0, %zmm0
	cmpq	%rdx, %rsi
	jne	.L399
	vmovapd	%zmm0, 64(%rsp)
.L398:
	vmovdqa	64(%rsp), %xmm6
	vmovdqa	80(%rsp), %xmm5
	vmovdqa	112(%rsp), %xmm2
	vmovdqa	%xmm6, (%r8)
	vmovdqa	96(%rsp), %xmm6
	vmovdqa	%xmm5, 16(%r8)
	vmovdqa	%xmm2, 48(%r8)
	vmovdqa	%xmm6, 32(%r8)
	vzeroupper
.L397:
	movl	12(%r9), %ecx
	vxorps	%xmm5, %xmm5, %xmm5
	testl	%ecx, %ecx
	jle	.L404
	vmovsd	(%r8), %xmm3
	vmovq	.LC5(%rip), %xmm6
	vminsd	.LC1(%rip), %xmm3, %xmm2
	vmaxsd	.LC3(%rip), %xmm3, %xmm1
	vaddsd	.LC4(%rip), %xmm3, %xmm0
	vandpd	%xmm6, %xmm3, %xmm4
	vmovq	.LC6(%rip), %xmm3
	vxorpd	%xmm3, %xmm4, %xmm4
	vmovsd	%xmm4, 80(%rsp)
	cmpl	$1, %ecx
	je	.L407
	vmovsd	8(%r8), %xmm4
	vminsd	%xmm2, %xmm4, %xmm2
	vmaxsd	%xmm1, %xmm4, %xmm1
	vaddsd	%xmm4, %xmm0, %xmm0
	vandpd	%xmm6, %xmm4, %xmm4
	vxorpd	%xmm3, %xmm4, %xmm4
	vmovsd	%xmm4, 88(%rsp)
	cmpl	$2, %ecx
	je	.L407
	vmovsd	16(%r8), %xmm4
	vminsd	%xmm2, %xmm4, %xmm2
	vmaxsd	%xmm1, %xmm4, %xmm1
	vaddsd	%xmm4, %xmm0, %xmm0
	vandpd	%xmm6, %xmm4, %xmm4
	vxorpd	%xmm3, %xmm4, %xmm4
	vmovsd	%xmm4, 96(%rsp)
	cmpl	$3, %ecx
	je	.L407
	vmovsd	24(%r8), %xmm4
	vminsd	%xmm2, %xmm4, %xmm2
	vmaxsd	%xmm1, %xmm4, %xmm1
	vaddsd	%xmm4, %xmm0, %xmm0
	vandpd	%xmm6, %xmm4, %xmm4
	vxorpd	%xmm3, %xmm4, %xmm4
	vmovsd	%xmm4, 104(%rsp)
	cmpl	$4, %ecx
	je	.L407
	vmovsd	32(%r8), %xmm4
	vminsd	%xmm2, %xmm4, %xmm2
	vmaxsd	%xmm1, %xmm4, %xmm1
	vaddsd	%xmm4, %xmm0, %xmm0
	vandpd	%xmm6, %xmm4, %xmm4
	vxorpd	%xmm3, %xmm4, %xmm4
	vmovsd	%xmm4, 112(%rsp)
	cmpl	$5, %ecx
	je	.L407
	vmovsd	40(%r8), %xmm4
	vminsd	%xmm2, %xmm4, %xmm2
	vmaxsd	%xmm1, %xmm4, %xmm1
	vaddsd	%xmm4, %xmm0, %xmm0
	vandpd	%xmm6, %xmm4, %xmm4
	vxorpd	%xmm3, %xmm4, %xmm4
	vmovsd	%xmm4, 120(%rsp)
.L407:
	vandpd	%xmm6, %xmm0, %xmm0
	vcvtsi2sdl	%ecx, %xmm5, %xmm5
	vxorpd	%xmm3, %xmm1, %xmm4
	vxorpd	%xmm3, %xmm0, %xmm0
	vxorpd	%xmm3, %xmm2, %xmm3
	vdivsd	%xmm5, %xmm0, %xmm0
	vcmpnltsd	%xmm4, %xmm2, %xmm2
	vblendvpd	%xmm2, %xmm3, %xmm1, %xmm1
	vunpcklpd	%xmm0, %xmm1, %xmm1
	vmovapd	%xmm1, 64(%rsp)
.L419:
	leaq	48(%rsp), %rax
	xorl	%r13d, %r13d
	leaq	64(%rsp), %rbx
	movq	%rax, 40(%rsp)
	.p2align 4
	.p2align 3
.L430:
	movq	8(%r15), %rax
	movq	%r13, %r12
	salq	$5, %r12
	addq	(%rax), %r12
	movq	(%r12), %rdx
	movq	8(%r12), %rax
	subq	%rdx, %rax
	cmpq	$752, %rax
	jbe	.L420
	vmovsd	(%rbx,%r13,8), %xmm0
	vcomisd	(%rdx), %xmm0
	jnb	.L421
.L420:
	vmovsd	(%rbx,%r13,8), %xmm0
	movq	40(%rsp), %rsi
	movl	%r14d, %eax
	movq	%r12, %rdi
	movq	%rax, 56(%rsp)
	vmovsd	%xmm0, 48(%rsp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	8(%r12), %r11
	movq	(%r12), %r9
	movq	%r11, %rdi
	vmovsd	-16(%r11), %xmm1
	movq	-8(%r11), %r10
	subq	%r9, %rdi
	movq	%rdi, %rax
	sarq	$4, %rax
	leaq	-1(%rax), %rcx
	subq	$2, %rax
	movq	%rax, %rsi
	shrq	$63, %rsi
	addq	%rax, %rsi
	sarq	%rsi
	testq	%rcx, %rcx
	jg	.L427
	jmp	.L475
	.p2align 4
	.p2align 3
.L423:
	cmpq	8(%rax), %r10
	jbe	.L473
.L425:
	vmovdqu	(%rax), %xmm7
	salq	$4, %rcx
	vmovdqu	%xmm7, (%r9,%rcx)
	leaq	-1(%rsi), %rcx
	movq	%rcx, %rdx
	shrq	$63, %rdx
	addq	%rcx, %rdx
	movq	%rsi, %rcx
	sarq	%rdx
	testq	%rsi, %rsi
	jle	.L426
	movq	%rdx, %rsi
.L427:
	movq	%rsi, %rax
	salq	$4, %rax
	addq	%r9, %rax
	vmovsd	(%rax), %xmm0
	vucomisd	%xmm0, %xmm1
	jp	.L447
	je	.L423
.L447:
	vcomisd	%xmm0, %xmm1
	ja	.L425
.L473:
	salq	$4, %rcx
	leaq	(%r9,%rcx), %rax
.L426:
	vmovsd	%xmm1, (%rax)
	movq	%r10, 8(%rax)
	cmpq	$768, %rdi
	ja	.L428
.L474:
	movq	(%r15), %rax
	movl	12(%rax), %ecx
.L421:
	incq	%r13
	leal	-1(%r13), %eax
	cmpl	%ecx, %eax
	jle	.L430
.L395:
	movq	184(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L476
	leaq	-40(%rbp), %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
	.p2align 4
	.p2align 3
.L428:
	.cfi_restore_state
	leaq	-16(%r11), %rax
	cmpq	$16, %rdi
	jg	.L477
.L429:
	movq	%rax, 8(%r12)
	jmp	.L474
	.p2align 4
	.p2align 3
.L477:
	vmovdqu	(%r9), %xmm5
	movq	-16(%r11), %rdx
	xorl	%esi, %esi
	movq	%r9, %rdi
	movq	-8(%r11), %rcx
	movq	%rax, 32(%rsp)
	vmovq	%rdx, %xmm0
	movq	%rax, %rdx
	subq	%r9, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm5, -16(%r11)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	movq	32(%rsp), %rax
	jmp	.L429
.L475:
	leaq	-16(%r9,%rdi), %rax
	jmp	.L426
.L404:
	vmovsd	.LC7(%rip), %xmm0
	vcvtsi2sdl	%ecx, %xmm5, %xmm5
	vmovsd	.LC3(%rip), %xmm7
	vdivsd	%xmm5, %xmm0, %xmm0
	vunpcklpd	%xmm0, %xmm7, %xmm0
	vmovapd	%xmm0, 64(%rsp)
	cmpl	$-1, %ecx
	jl	.L395
	jmp	.L419
.L476:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE6028:
	.size	_ZZN9Optimizer14informed_seedsEvENKUljE_clEj, .-_ZZN9Optimizer14informed_seedsEvENKUljE_clEj
	.section	.text._ZN11TableSearch5visitEid,"axG",@progbits,_ZN11TableSearch5visitEid,comdat
	.align 2
	.p2align 4
	.weak	_ZN11TableSearch5visitEid
	.type	_ZN11TableSearch5visitEid, @function
_ZN11TableSearch5visitEid:
.LFB6149:
	.cfi_startproc
	endbr64
	leaq	8(%rsp), %r10
	.cfi_def_cfa 10, 0
	andq	$-64, %rsp
	vmovsd	%xmm0, %xmm0, %xmm2
	pushq	-8(%r10)
	pushq	%rbp
	movq	%rsp, %rbp
	.cfi_escape 0x10,0x6,0x2,0x76,0
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%r10
	.cfi_escape 0xf,0x3,0x76,0x58,0x6
	.cfi_escape 0x10,0xf,0x2,0x76,0x78
	.cfi_escape 0x10,0xe,0x2,0x76,0x70
	.cfi_escape 0x10,0xd,0x2,0x76,0x68
	.cfi_escape 0x10,0xc,0x2,0x76,0x60
	pushq	%rbx
	movl	%esi, %r15d
	subq	$64, %rsp
	.cfi_escape 0x10,0x3,0x2,0x76,0x50
	movq	192(%rdi), %rax
	movq	%rdi, %rbx
	incq	%rax
	movq	%rax, 192(%rdi)
	testl	$4095, %eax
	je	.L590
.L479:
	cmpb	$0, 208(%rbx)
	jne	.L587
	vmovsd	(%rbx), %xmm1
	vaddsd	176(%rbx), %xmm2, %xmm0
	vsubsd	.LC8(%rip), %xmm1, %xmm1
	vcomisd	%xmm1, %xmm0
	jnb	.L587
	movl	184(%rbx), %edx
	testl	%edx, %edx
	jle	.L513
	movslq	%r15d, %rax
	vmovsd	112(%rbx), %xmm0
	salq	$6, %rax
	addq	88(%rbx), %rax
	vaddsd	(%rax), %xmm0, %xmm3
	vcomisd	%xmm1, %xmm3
	jnb	.L587
	vmaxsd	.LC3(%rip), %xmm0, %xmm0
	cmpl	$1, %edx
	je	.L482
	vmovsd	120(%rbx), %xmm3
	vaddsd	8(%rax), %xmm3, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L587
	vmaxsd	%xmm0, %xmm3, %xmm3
	cmpl	$2, %edx
	je	.L516
	vmovsd	128(%rbx), %xmm0
	vaddsd	16(%rax), %xmm0, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L587
	vmaxsd	%xmm3, %xmm0, %xmm0
	cmpl	$3, %edx
	je	.L482
	vmovsd	136(%rbx), %xmm3
	vaddsd	24(%rax), %xmm3, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L587
	vmaxsd	%xmm0, %xmm3, %xmm3
	cmpl	$4, %edx
	je	.L516
	vmovsd	144(%rbx), %xmm0
	vaddsd	32(%rax), %xmm0, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L587
	vmaxsd	%xmm3, %xmm0, %xmm0
	cmpl	$5, %edx
	je	.L482
	vmovsd	152(%rbx), %xmm3
	vaddsd	40(%rax), %xmm3, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L587
	vmaxsd	%xmm0, %xmm3, %xmm3
	cmpl	$6, %edx
	je	.L516
	vmovsd	160(%rbx), %xmm4
	vaddsd	48(%rax), %xmm4, %xmm0
	vcomisd	%xmm1, %xmm0
	jnb	.L587
	vmaxsd	%xmm3, %xmm4, %xmm4
	cmpl	$7, %edx
	je	.L517
	vmovsd	168(%rbx), %xmm0
	vaddsd	56(%rax), %xmm0, %xmm3
	vcomisd	%xmm1, %xmm3
	jnb	.L587
	vmaxsd	%xmm4, %xmm0, %xmm0
.L482:
	vcomisd	%xmm0, %xmm1
	ja	.L591
.L491:
	movq	64(%rbx), %rdx
	movq	72(%rbx), %rax
	subq	%rdx, %rax
	sarq	$5, %rax
	imull	$-1431655765, %eax, %eax
	cmpl	%r15d, %eax
	je	.L587
	movslq	%r15d, %rax
	movq	216(%rbx), %rsi
	leaq	112(%rbx), %r13
	movq	%rdx, -64(%rbp)
	leaq	(%rax,%rax,2), %r12
	movq	%r12, %r14
	salq	$5, %r14
	leaq	(%rdx,%r14), %rcx
	movq	8352(%rsi), %rdi
	movq	40(%rbx), %rsi
	movq	%r14, -96(%rbp)
	movslq	(%rcx), %rax
	movl	(%rsi,%rax,4), %esi
	cmpl	%esi, (%rdi,%rax,4)
	leaq	40(%rdx,%r14), %rsi
	leaq	0(,%r12,4), %rax
	movq	%rax, -72(%rbp)
	movq	%rcx, %r14
	setne	-56(%rbp)
	subq	%rsi, %r13
	xorl	%r12d, %r12d
	movq	%r13, -88(%rbp)
	movl	%r12d, %r13d
.L496:
	movl	%r13d, %esi
	xorl	$1, %esi
	cmpb	-56(%rbp), %sil
	jne	.L493
	vaddsd	176(%rbx), %xmm2, %xmm1
	vmovsd	8(%r14), %xmm3
	vmovsd	(%rbx), %xmm0
	vsubsd	.LC8(%rip), %xmm0, %xmm0
	vaddsd	%xmm3, %xmm1, %xmm1
	vcomisd	%xmm0, %xmm1
	jb	.L585
	cmpl	$1, %r13d
	jne	.L592
.L586:
	vzeroupper
.L587:
	addq	$64, %rsp
	popq	%rbx
	popq	%r10
	.cfi_remember_state
	.cfi_def_cfa 10, 0
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	leaq	-8(%r10), %rsp
	.cfi_def_cfa 7, 8
	ret
	.p2align 4
	.p2align 3
.L590:
	.cfi_restore_state
	vmovsd	%xmm0, -56(%rbp)
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	cmpq	200(%rbx), %rax
	vmovsd	-56(%rbp), %xmm2
	jl	.L479
	movb	$1, 208(%rbx)
	jmp	.L587
	.p2align 4
	.p2align 3
.L591:
	movl	188(%rbx), %eax
	vmovsd	%xmm0, (%rbx)
	leaq	40(%rbx), %rsi
	leaq	16(%rbx), %rdi
	vmovsd	%xmm2, -56(%rbp)
	movl	%eax, 8(%rbx)
	call	_ZNSt6vectorIiSaIiEEaSERKS1_.isra.0
	vmovsd	-56(%rbp), %xmm2
	jmp	.L491
	.p2align 4
	.p2align 3
.L493:
	leal	1(%r15), %esi
	vmovsd	%xmm2, %xmm2, %xmm0
	movq	%rbx, %rdi
	vmovsd	%xmm2, -80(%rbp)
	vzeroupper
	call	_ZN11TableSearch5visitEid
	vmovsd	-80(%rbp), %xmm2
.L511:
	cmpb	$0, 208(%rbx)
	jne	.L586
	cmpl	$1, %r13d
	je	.L586
.L592:
	movl	$1, %r13d
	jmp	.L496
	.p2align 4
	.p2align 3
.L585:
	movq	40(%rbx), %rsi
	movslq	(%r14), %rdi
	xorl	$1, (%rsi,%rdi,4)
	movl	184(%rbx), %esi
	testl	%esi, %esi
	jle	.L497
	cmpq	$48, -88(%rbp)
	movl	%esi, %r9d
	leal	-1(%rsi), %edi
	jbe	.L498
	cmpl	$2, %edi
	jbe	.L498
	cmpl	$6, %edi
	jbe	.L519
	movq	-64(%rbp), %rax
	movq	-96(%rbp), %rcx
	movl	%esi, %edi
	andl	$-8, %edi
	movl	%edi, %r8d
	vmovupd	32(%rax,%rcx), %zmm7
	vaddpd	112(%rbx), %zmm7, %zmm0
	vmovupd	%zmm0, 112(%rbx)
	cmpl	%edi, %esi
	je	.L497
	subl	%edi, %r9d
	leal	-1(%r9), %r10d
	cmpl	$2, %r10d
	jbe	.L501
.L499:
	movq	-72(%rbp), %rax
	leaq	112(%rbx,%rdi,8), %r10
	vmovupd	(%r10), %ymm5
	leaq	4(%rdi,%rax), %rdi
	movq	-64(%rbp), %rax
	vaddpd	(%rax,%rdi,8), %ymm5, %ymm0
	movl	%r9d, %edi
	andl	$-4, %edi
	addl	%edi, %r8d
	vmovupd	%ymm0, (%r10)
	cmpl	%r9d, %edi
	je	.L497
.L501:
	movslq	%r8d, %r9
	salq	$3, %r9
	leaq	(%rbx,%r9), %rdi
	leaq	(%r14,%r9), %r10
	vmovsd	112(%rdi), %xmm0
	vaddsd	32(%r14,%r9), %xmm0, %xmm0
	leal	1(%r8), %r9d
	vmovsd	%xmm0, 112(%rdi)
	cmpl	%r9d, %esi
	jle	.L497
	vmovsd	120(%rdi), %xmm0
	addl	$2, %r8d
	vaddsd	40(%r10), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rdi)
	cmpl	%r8d, %esi
	jle	.L497
	vmovsd	128(%rdi), %xmm0
	vaddsd	48(%r10), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rdi)
.L497:
	vaddsd	%xmm2, %xmm3, %xmm0
	leal	1(%r15), %esi
	movq	%rbx, %rdi
	vmovsd	%xmm2, -80(%rbp)
	vzeroupper
	call	_ZN11TableSearch5visitEid
	movl	184(%rbx), %esi
	vmovsd	-80(%rbp), %xmm2
	testl	%esi, %esi
	jle	.L504
	cmpq	$48, -88(%rbp)
	movl	%esi, %r9d
	leal	-1(%rsi), %edi
	jbe	.L505
	cmpl	$2, %edi
	jbe	.L505
	cmpl	$6, %edi
	jbe	.L520
	movq	-64(%rbp), %rax
	movq	-96(%rbp), %rcx
	movl	%esi, %edi
	vmovupd	112(%rbx), %zmm7
	andl	$-8, %edi
	movl	%edi, %r8d
	vsubpd	32(%rax,%rcx), %zmm7, %zmm0
	vmovupd	%zmm0, 112(%rbx)
	cmpl	%edi, %esi
	je	.L504
	subl	%edi, %r9d
	leal	-1(%r9), %r10d
	cmpl	$2, %r10d
	jbe	.L508
.L506:
	movq	-72(%rbp), %rax
	leaq	112(%rbx,%rdi,8), %r10
	vmovupd	(%r10), %ymm6
	leaq	4(%rdi,%rax), %rdi
	movq	-64(%rbp), %rax
	vsubpd	(%rax,%rdi,8), %ymm6, %ymm0
	movl	%r9d, %edi
	andl	$-4, %edi
	addl	%edi, %r8d
	vmovupd	%ymm0, (%r10)
	cmpl	%r9d, %edi
	je	.L504
.L508:
	movslq	%r8d, %r9
	salq	$3, %r9
	leaq	(%rbx,%r9), %rdi
	leaq	(%r14,%r9), %r10
	vmovsd	112(%rdi), %xmm0
	vsubsd	32(%r14,%r9), %xmm0, %xmm0
	leal	1(%r8), %r9d
	vmovsd	%xmm0, 112(%rdi)
	cmpl	%r9d, %esi
	jle	.L504
	vmovsd	120(%rdi), %xmm0
	addl	$2, %r8d
	vsubsd	40(%r10), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rdi)
	cmpl	%r8d, %esi
	jle	.L504
	vmovsd	128(%rdi), %xmm0
	vsubsd	48(%r10), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rdi)
.L504:
	movslq	(%r14), %rdi
	movq	40(%rbx), %rsi
	xorl	$1, (%rsi,%rdi,4)
	jmp	.L511
.L505:
	vmovsd	112(%rbx), %xmm0
	vsubsd	32(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 112(%rbx)
	cmpl	$1, %esi
	je	.L504
	vmovsd	120(%rbx), %xmm0
	vsubsd	40(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rbx)
	cmpl	$2, %esi
	je	.L504
	vmovsd	128(%rbx), %xmm0
	vsubsd	48(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rbx)
	cmpl	$3, %esi
	je	.L504
	vmovsd	136(%rbx), %xmm0
	vsubsd	56(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 136(%rbx)
	cmpl	$4, %esi
	je	.L504
	vmovsd	144(%rbx), %xmm0
	vsubsd	64(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 144(%rbx)
	cmpl	$5, %esi
	je	.L504
	vmovsd	152(%rbx), %xmm0
	vsubsd	72(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 152(%rbx)
	cmpl	$6, %esi
	je	.L504
	vmovsd	160(%rbx), %xmm0
	vsubsd	80(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 160(%rbx)
	cmpl	$7, %esi
	je	.L504
	vmovsd	168(%rbx), %xmm0
	vsubsd	88(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 168(%rbx)
	jmp	.L504
.L498:
	vmovsd	112(%rbx), %xmm0
	vaddsd	32(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 112(%rbx)
	cmpl	$1, %esi
	je	.L497
	vmovsd	120(%rbx), %xmm0
	vaddsd	40(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rbx)
	cmpl	$2, %esi
	je	.L497
	vmovsd	128(%rbx), %xmm0
	vaddsd	48(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rbx)
	cmpl	$3, %esi
	je	.L497
	vmovsd	136(%rbx), %xmm0
	vaddsd	56(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 136(%rbx)
	cmpl	$4, %esi
	je	.L497
	vmovsd	144(%rbx), %xmm0
	vaddsd	64(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 144(%rbx)
	cmpl	$5, %esi
	je	.L497
	vmovsd	152(%rbx), %xmm0
	vaddsd	72(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 152(%rbx)
	cmpl	$6, %esi
	je	.L497
	vmovsd	160(%rbx), %xmm0
	vaddsd	80(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 160(%rbx)
	cmpl	$7, %esi
	je	.L497
	vmovsd	168(%rbx), %xmm0
	vaddsd	88(%r14), %xmm0, %xmm0
	vmovsd	%xmm0, 168(%rbx)
	jmp	.L497
	.p2align 4
	.p2align 3
.L516:
	vmovsd	%xmm3, %xmm3, %xmm0
	jmp	.L482
.L513:
	vmovsd	.LC3(%rip), %xmm0
	jmp	.L482
.L517:
	vmovsd	%xmm4, %xmm4, %xmm0
	jmp	.L482
.L519:
	xorl	%edi, %edi
	xorl	%r8d, %r8d
	jmp	.L499
.L520:
	xorl	%r8d, %r8d
	xorl	%edi, %edi
	jmp	.L506
	.cfi_endproc
.LFE6149:
	.size	_ZN11TableSearch5visitEid, .-_ZN11TableSearch5visitEid
	.section	.text._ZN11TableSearchD2Ev,"axG",@progbits,_ZN11TableSearchD5Ev,comdat
	.align 2
	.p2align 4
	.weak	_ZN11TableSearchD2Ev
	.type	_ZN11TableSearchD2Ev, @function
_ZN11TableSearchD2Ev:
.LFB6171:
	.cfi_startproc
	endbr64
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset 3, -16
	movq	%rdi, %rbx
	movq	88(%rdi), %rdi
	testq	%rdi, %rdi
	je	.L594
	movq	104(%rbx), %rsi
	movl	$32, %edx
	subq	%rdi, %rsi
	call	_ZdlPvmSt11align_val_t@PLT
.L594:
	movq	64(%rbx), %rdi
	testq	%rdi, %rdi
	je	.L595
	movq	80(%rbx), %rsi
	movl	$32, %edx
	subq	%rdi, %rsi
	call	_ZdlPvmSt11align_val_t@PLT
.L595:
	movq	40(%rbx), %rdi
	testq	%rdi, %rdi
	je	.L596
	movq	56(%rbx), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L596:
	movq	16(%rbx), %rdi
	testq	%rdi, %rdi
	je	.L607
	movq	32(%rbx), %rsi
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 8
	subq	%rdi, %rsi
	jmp	_ZdlPvm@PLT
	.p2align 4
	.p2align 3
.L607:
	.cfi_restore_state
	popq	%rbx
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE6171:
	.size	_ZN11TableSearchD2Ev, .-_ZN11TableSearchD2Ev
	.weak	_ZN11TableSearchD1Ev
	.set	_ZN11TableSearchD1Ev,_ZN11TableSearchD2Ev
	.section	.text._ZN9OptimizerD2Ev,"axG",@progbits,_ZN9OptimizerD5Ev,comdat
	.align 2
	.p2align 4
	.weak	_ZN9OptimizerD2Ev
	.type	_ZN9OptimizerD2Ev, @function
_ZN9OptimizerD2Ev:
.LFB6174:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	movq	%rdi, %rbp
	subq	$8, %rsp
	.cfi_def_cfa_offset 32
	movq	256(%rdi), %rbx
	testq	%rbx, %rbx
	je	.L610
	.p2align 4
	.p2align 3
.L611:
	movq	%rbx, %rdi
	movq	(%rbx), %rbx
	movl	$16, %esi
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L611
.L610:
	movq	248(%rbp), %rax
	movq	240(%rbp), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	240(%rbp), %rdi
	leaq	288(%rbp), %rax
	movq	$0, 264(%rbp)
	movq	248(%rbp), %rsi
	movq	$0, 256(%rbp)
	cmpq	%rax, %rdi
	je	.L612
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L612:
	movq	208(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L613
	movq	224(%rbp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L613:
	movq	176(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L614
	movq	192(%rbp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L614:
	movq	136(%rbp), %rbx
	testq	%rbx, %rbx
	je	.L615
	.p2align 4
	.p2align 3
.L616:
	movq	%rbx, %rdi
	movq	(%rbx), %rbx
	movl	$32, %esi
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L616
.L615:
	movq	128(%rbp), %rax
	movq	120(%rbp), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	120(%rbp), %rdi
	leaq	168(%rbp), %rax
	movq	$0, 144(%rbp)
	movq	128(%rbp), %rsi
	movq	$0, 136(%rbp)
	cmpq	%rax, %rdi
	je	.L617
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L617:
	movq	96(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L618
	movq	112(%rbp), %rsi
	movl	$32, %edx
	subq	%rdi, %rsi
	call	_ZdlPvmSt11align_val_t@PLT
.L618:
	movq	72(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L619
	movq	88(%rbp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L619:
	movq	48(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L620
	movq	64(%rbp), %rsi
	movl	$32, %edx
	subq	%rdi, %rsi
	call	_ZdlPvmSt11align_val_t@PLT
.L620:
	movq	24(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L645
	movq	40(%rbp), %rsi
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	subq	%rdi, %rsi
	jmp	_ZdlPvm@PLT
	.p2align 4
	.p2align 3
.L645:
	.cfi_restore_state
	addq	$8, %rsp
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE6174:
	.size	_ZN9OptimizerD2Ev, .-_ZN9OptimizerD2Ev
	.weak	_ZN9OptimizerD1Ev
	.set	_ZN9OptimizerD1Ev,_ZN9OptimizerD2Ev
	.section	.text._ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev,"axG",@progbits,_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED5Ev,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev
	.type	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev, @function
_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev:
.LFB6592:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	movq	%rdi, %rbp
	subq	$8, %rsp
	.cfi_def_cfa_offset 32
	movq	16(%rdi), %rbx
	testq	%rbx, %rbx
	je	.L648
	.p2align 4
	.p2align 3
.L649:
	movq	%rbx, %rdi
	movq	(%rbx), %rbx
	movl	$16, %esi
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L649
.L648:
	movq	8(%rbp), %rax
	movq	0(%rbp), %rdi
	xorl	%esi, %esi
	addq	$48, %rbp
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	-48(%rbp), %rdi
	movq	$0, -24(%rbp)
	movq	$0, -32(%rbp)
	movq	-40(%rbp), %rsi
	cmpq	%rbp, %rdi
	je	.L655
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	salq	$3, %rsi
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	jmp	_ZdlPvm@PLT
	.p2align 4
	.p2align 3
.L655:
	.cfi_restore_state
	addq	$8, %rsp
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE6592:
	.size	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev, .-_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev
	.weak	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED1Ev
	.set	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED1Ev,_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev
	.section	.text._ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED2Ev,"axG",@progbits,_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED5Ev,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED2Ev
	.type	_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED2Ev, @function
_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED2Ev:
.LFB6712:
	.cfi_startproc
	endbr64
	pushq	%r12
	.cfi_def_cfa_offset 16
	.cfi_offset 12, -16
	pushq	%rbp
	.cfi_def_cfa_offset 24
	.cfi_offset 6, -24
	pushq	%rbx
	.cfi_def_cfa_offset 32
	.cfi_offset 3, -32
	movq	%rdi, %r12
	movq	8(%rdi), %rbx
	movq	(%rdi), %rbp
	cmpq	%rbp, %rbx
	je	.L658
	.p2align 4
	.p2align 3
.L662:
	movq	0(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L659
	movq	16(%rbp), %rsi
	addq	$32, %rbp
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	cmpq	%rbp, %rbx
	jne	.L662
.L661:
	movq	(%r12), %rbp
.L658:
	testq	%rbp, %rbp
	je	.L664
	movq	16(%r12), %rsi
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	movq	%rbp, %rdi
	subq	%rbp, %rsi
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	jmp	_ZdlPvm@PLT
	.p2align 4
	.p2align 3
.L659:
	.cfi_restore_state
	addq	$32, %rbp
	cmpq	%rbp, %rbx
	jne	.L662
	jmp	.L661
	.p2align 4
	.p2align 3
.L664:
	popq	%rbx
	.cfi_def_cfa_offset 24
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE6712:
	.size	_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED2Ev, .-_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED2Ev
	.weak	_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED1Ev
	.set	_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED1Ev,_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED2Ev
	.section	.text._ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev,"axG",@progbits,_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED5Ev,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev
	.type	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev, @function
_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev:
.LFB6761:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	movq	%rdi, %rbp
	subq	$8, %rsp
	.cfi_def_cfa_offset 32
	movq	16(%rdi), %rbx
	testq	%rbx, %rbx
	je	.L667
	.p2align 4
	.p2align 3
.L668:
	movq	%rbx, %rdi
	movq	(%rbx), %rbx
	movl	$16, %esi
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L668
.L667:
	movq	8(%rbp), %rax
	movq	0(%rbp), %rdi
	xorl	%esi, %esi
	addq	$48, %rbp
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	-48(%rbp), %rdi
	movq	$0, -24(%rbp)
	movq	$0, -32(%rbp)
	movq	-40(%rbp), %rsi
	cmpq	%rbp, %rdi
	je	.L674
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	salq	$3, %rsi
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	jmp	_ZdlPvm@PLT
	.p2align 4
	.p2align 3
.L674:
	.cfi_restore_state
	addq	$8, %rsp
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE6761:
	.size	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev, .-_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev
	.weak	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED1Ev
	.set	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED1Ev,_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED2Ev
	.section	.rodata._ZNSt6vectorI5StateSaIS0_EE6insertIN9__gnu_cxx17__normal_iteratorIPS0_S2_EEvEES7_NS5_IPKS0_S2_EET_SB_.str1.1,"aMS",@progbits,1
.LC9:
	.string	"vector::_M_range_insert"
	.section	.text._ZNSt6vectorI5StateSaIS0_EE6insertIN9__gnu_cxx17__normal_iteratorIPS0_S2_EEvEES7_NS5_IPKS0_S2_EET_SB_,"axG",@progbits,_ZNSt6vectorI5StateSaIS0_EE6insertIN9__gnu_cxx17__normal_iteratorIPS0_S2_EEvEES7_NS5_IPKS0_S2_EET_SB_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI5StateSaIS0_EE6insertIN9__gnu_cxx17__normal_iteratorIPS0_S2_EEvEES7_NS5_IPKS0_S2_EET_SB_
	.type	_ZNSt6vectorI5StateSaIS0_EE6insertIN9__gnu_cxx17__normal_iteratorIPS0_S2_EEvEES7_NS5_IPKS0_S2_EET_SB_, @function
_ZNSt6vectorI5StateSaIS0_EE6insertIN9__gnu_cxx17__normal_iteratorIPS0_S2_EEvEES7_NS5_IPKS0_S2_EET_SB_:
.LFB6860:
	.cfi_startproc
	endbr64
	movq	(%rdi), %r11
	movq	%rsi, %rax
	cmpq	%rdx, %rcx
	je	.L706
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	subq	%r11, %rax
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rcx, %r15
	subq	$40, %rsp
	.cfi_def_cfa_offset 96
	movq	8(%rdi), %r9
	subq	%rdx, %r15
	movq	%rdi, %rbx
	movq	%rax, (%rsp)
	movq	16(%rdi), %rax
	movq	%r15, %r12
	movq	%rsi, %rbp
	movq	%rdx, %r13
	sarq	$4, %r12
	subq	%r9, %rax
	cmpq	%r15, %rax
	jb	.L678
	movq	%r9, %r14
	subq	%rsi, %r14
	cmpq	%r14, %r15
	jnb	.L679
	movq	%r9, %r12
	movq	%r15, %rdx
	movq	%r9, %rdi
	subq	%r15, %r12
	movq	%r12, %rsi
	call	memmove@PLT
	addq	%r15, 8(%rbx)
	cmpq	%r12, %rbp
	je	.L680
	movq	%r12, %rdx
	movq	%rax, %rdi
	subq	%rbp, %rdx
	movq	%rbp, %rsi
	subq	%rdx, %rdi
	call	memmove@PLT
.L680:
	movq	%r15, %rdx
.L710:
	movq	%r13, %rsi
	movq	%rbp, %rdi
	call	memmove@PLT
.L709:
	movq	(%rsp), %rax
	addq	(%rbx), %rax
	addq	$40, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L678:
	.cfi_restore_state
	subq	%r11, %r9
	movabsq	$576460752303423487, %rax
	sarq	$4, %r9
	subq	%r9, %rax
	cmpq	%rax, %r12
	ja	.L711
	cmpq	%r9, %r12
	cmovb	%r9, %r12
	addq	%r9, %r12
	jc	.L686
	testq	%r12, %r12
	jne	.L712
	movq	(%rsp), %rdx
	xorl	%r12d, %r12d
	movq	$0, 8(%rsp)
.L688:
	movq	8(%rsp), %rdi
	leaq	(%rdi,%rdx), %r9
	leaq	(%r9,%r15), %r14
	cmpq	%r11, %rbp
	je	.L689
	movq	%r11, %rsi
	movq	%r11, 16(%rsp)
	movq	%r9, 24(%rsp)
	call	memmove@PLT
	movq	%r15, %rdx
	movq	%r13, %rsi
	movq	24(%rsp), %rdi
	call	memcpy@PLT
	movq	8(%rbx), %rdx
	movq	16(%rsp), %r11
	movq	%rdx, %rax
	subq	%rbp, %rax
	cmpq	%rdx, %rbp
	je	.L713
.L690:
	movq	%rax, %rdx
	movq	%rbp, %rsi
	movq	%r14, %rdi
	movq	%r11, 16(%rsp)
	movq	%rax, %r13
	call	memcpy@PLT
	movq	16(%rsp), %r11
.L692:
	addq	%r13, %r14
	testq	%r11, %r11
	jne	.L714
.L693:
	vmovq	8(%rsp), %xmm1
	movq	%r12, 16(%rbx)
	vpinsrq	$1, %r14, %xmm1, %xmm0
	vmovq	%xmm1, %rax
	addq	(%rsp), %rax
	vmovdqu	%xmm0, (%rbx)
	addq	$40, %rsp
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L706:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L679:
	.cfi_def_cfa_offset 96
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	leaq	(%rdx,%r14), %r15
	movq	%r9, %rdi
	cmpq	%r15, %rcx
	je	.L681
	movq	%rcx, %rdx
	movq	%r15, %rsi
	subq	%r15, %rdx
	call	memmove@PLT
	movq	8(%rbx), %rdi
	movq	%rax, %r9
.L681:
	movq	%r14, %rax
	sarq	$4, %rax
	subq	%rax, %r12
	salq	$4, %r12
	addq	%r12, %rdi
	movq	%rdi, 8(%rbx)
	cmpq	%r9, %rbp
	je	.L682
	movq	%r14, %rdx
	movq	%rbp, %rsi
	call	memmove@PLT
	movq	8(%rbx), %rdi
.L682:
	addq	%r14, %rdi
	movq	%r14, %rdx
	movq	%rdi, 8(%rbx)
	cmpq	%r13, %r15
	jne	.L710
	jmp	.L709
	.p2align 4
	.p2align 3
.L689:
	movq	%r13, %rsi
	movq	%r15, %rdx
	movq	%r9, %rdi
	movq	%r11, 16(%rsp)
	call	memcpy@PLT
	xorl	%r13d, %r13d
	movq	8(%rbx), %rcx
	movq	16(%rsp), %r11
	movq	%rcx, %rax
	subq	%rbp, %rax
	cmpq	%rbp, %rcx
	jne	.L690
	jmp	.L692
	.p2align 4
	.p2align 3
.L714:
	movq	16(%rbx), %rsi
	subq	%r11, %rsi
.L694:
	movq	%r11, %rdi
	call	_ZdlPvm@PLT
	jmp	.L693
	.p2align 4
	.p2align 3
.L713:
	movq	16(%rbx), %rsi
	addq	%rax, %r14
	subq	%r11, %rsi
	jmp	.L694
.L712:
	movabsq	$576460752303423487, %rax
	cmpq	%rax, %r12
	cmova	%rax, %r12
	salq	$4, %r12
.L687:
	movq	%r12, %rdi
	call	_Znwm@PLT
	movq	(%rbx), %r11
	movq	%rbp, %rdx
	movq	%rax, 8(%rsp)
	addq	%rax, %r12
	subq	%r11, %rdx
	jmp	.L688
.L686:
	movabsq	$9223372036854775792, %r12
	jmp	.L687
.L711:
	leaq	.LC9(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE6860:
	.size	_ZNSt6vectorI5StateSaIS0_EE6insertIN9__gnu_cxx17__normal_iteratorIPS0_S2_EEvEES7_NS5_IPKS0_S2_EET_SB_, .-_ZNSt6vectorI5StateSaIS0_EE6insertIN9__gnu_cxx17__normal_iteratorIPS0_S2_EEvEES7_NS5_IPKS0_S2_EET_SB_
	.section	.rodata._ZNSt6vectorIjSaIjEE17_M_default_appendEm.str1.1,"aMS",@progbits,1
.LC10:
	.string	"vector::_M_default_append"
	.section	.text._ZNSt6vectorIjSaIjEE17_M_default_appendEm,"axG",@progbits,_ZNSt6vectorIjSaIjEE17_M_default_appendEm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorIjSaIjEE17_M_default_appendEm
	.type	_ZNSt6vectorIjSaIjEE17_M_default_appendEm, @function
_ZNSt6vectorIjSaIjEE17_M_default_appendEm:
.LFB7100:
	.cfi_startproc
	endbr64
	testq	%rsi, %rsi
	je	.L745
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movabsq	$2305843009213693951, %rcx
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rdi, %r12
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %rdx
	movq	(%rdi), %r14
	movq	%rsi, %rbx
	movq	16(%rdi), %rax
	movq	%rdx, %rbp
	subq	%r14, %rbp
	subq	%rdx, %rax
	movq	%rbp, %r13
	sarq	$2, %rax
	sarq	$2, %r13
	subq	%r13, %rcx
	cmpq	%rax, %rsi
	jbe	.L748
	cmpq	%rsi, %rcx
	jb	.L749
	cmpq	%r13, %rsi
	movq	%r13, %rax
	cmovnb	%rsi, %rax
	addq	%r13, %rax
	jc	.L721
	testq	%rax, %rax
	jne	.L750
	movq	%rbp, %r8
	xorl	%r15d, %r15d
	xorl	%ecx, %ecx
.L723:
	movq	%rbx, %rdx
	addq	%rcx, %rbp
	decq	%rdx
	movl	$0, 0(%rbp)
	je	.L727
	leaq	4(%rbp), %rdi
	salq	$2, %rdx
	xorl	%esi, %esi
	movq	%r8, 8(%rsp)
	movq	%rcx, (%rsp)
	call	memset@PLT
	movq	(%rsp), %rcx
	movq	8(%rsp), %r8
.L727:
	testq	%r8, %r8
	jg	.L751
	testq	%r14, %r14
	jne	.L752
.L729:
	addq	%r13, %rbx
	vmovq	%rcx, %xmm1
	movq	%r15, 16(%r12)
	leaq	(%rcx,%rbx,4), %rax
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqu	%xmm0, (%r12)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L748:
	.cfi_restore_state
	decq	%rbx
	movl	$0, (%rdx)
	leaq	4(%rdx), %rcx
	je	.L718
	leaq	(%rcx,%rbx,4), %rax
	movq	%rcx, %rdi
	xorl	%esi, %esi
	subq	%rdx, %rax
	leaq	-4(%rax), %rbx
	movq	%rbx, %rdx
	call	memset@PLT
	movq	%rax, %rcx
	addq	%rbx, %rcx
.L718:
	movq	%rcx, 8(%r12)
	addq	$24, %rsp
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L745:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L751:
	.cfi_def_cfa_offset 80
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	movq	%r14, %rsi
	movq	%rcx, %rdi
	movq	%r8, %rdx
	call	memmove@PLT
	movq	16(%r12), %rsi
	movq	%rax, %rcx
	subq	%r14, %rsi
.L728:
	movq	%r14, %rdi
	movq	%rcx, (%rsp)
	call	_ZdlPvm@PLT
	movq	(%rsp), %rcx
	jmp	.L729
	.p2align 4
	.p2align 3
.L752:
	movq	16(%r12), %rsi
	subq	%r14, %rsi
	jmp	.L728
.L750:
	movabsq	$2305843009213693951, %r15
	cmpq	%r15, %rax
	cmovbe	%rax, %r15
	salq	$2, %r15
.L722:
	movq	%r15, %rdi
	call	_Znwm@PLT
	movq	(%r12), %r14
	movq	8(%r12), %r8
	movq	%rax, %rcx
	addq	%rax, %r15
	subq	%r14, %r8
	jmp	.L723
.L721:
	movabsq	$9223372036854775804, %r15
	jmp	.L722
.L749:
	leaq	.LC10(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7100:
	.size	_ZNSt6vectorIjSaIjEE17_M_default_appendEm, .-_ZNSt6vectorIjSaIjEE17_M_default_appendEm
	.section	.text._ZNSt6vectorI7ChannelSaIS0_EE17_M_default_appendEm,"axG",@progbits,_ZNSt6vectorI7ChannelSaIS0_EE17_M_default_appendEm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI7ChannelSaIS0_EE17_M_default_appendEm
	.type	_ZNSt6vectorI7ChannelSaIS0_EE17_M_default_appendEm, @function
_ZNSt6vectorI7ChannelSaIS0_EE17_M_default_appendEm:
.LFB7110:
	.cfi_startproc
	endbr64
	testq	%rsi, %rsi
	je	.L787
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movabsq	$-3208129404123400281, %rcx
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movabsq	$12531755484857032, %rdx
	subq	$40, %rsp
	.cfi_def_cfa_offset 96
	movq	8(%rdi), %r15
	movq	(%rdi), %r14
	movq	%rdi, %rbp
	movq	16(%rdi), %rax
	movq	%rsi, %rbx
	movq	%r15, %r13
	subq	%r14, %r13
	subq	%r15, %rax
	movq	%r13, %r12
	sarq	$5, %rax
	sarq	$5, %r12
	imulq	%rcx, %rax
	imulq	%rcx, %r12
	subq	%r12, %rdx
	cmpq	%rax, %rsi
	jbe	.L790
	cmpq	%rsi, %rdx
	jb	.L791
	cmpq	%r12, %rsi
	movq	%r12, %rax
	cmovnb	%rsi, %rax
	addq	%r12, %rax
	jc	.L760
	testq	%rax, %rax
	jne	.L792
	movq	%r13, 16(%rsp)
	movq	$0, 24(%rsp)
	movq	$0, 8(%rsp)
.L762:
	xorl	%esi, %esi
	movl	$736, %edx
	addq	8(%rsp), %r13
	movq	%r13, %rdi
	call	memset@PLT
	movq	%rbx, %rax
	decq	%rax
	je	.L767
	imulq	$736, %rax, %rax
	leaq	736(%r13), %rcx
	leaq	736(%r13,%rax), %r15
	.p2align 4
	.p2align 3
.L766:
	movq	%rcx, %rdi
	movl	$736, %edx
	movq	%r13, %rsi
	call	memcpy@PLT
	movq	%rax, %rcx
	addq	$736, %rcx
	cmpq	%rcx, %r15
	jne	.L766
.L767:
	cmpq	$0, 16(%rsp)
	jg	.L793
	testq	%r14, %r14
	jne	.L794
.L769:
	vmovq	8(%rsp), %xmm1
	addq	%r12, %rbx
	movq	24(%rsp), %rax
	imulq	$736, %rbx, %rbx
	addq	8(%rsp), %rbx
	movq	%rax, 16(%rbp)
	vpinsrq	$1, %rbx, %xmm1, %xmm0
	vmovdqu	%xmm0, 0(%rbp)
	addq	$40, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L790:
	.cfi_restore_state
	xorl	%esi, %esi
	movl	$736, %edx
	movq	%r15, %rdi
	leaq	736(%r15), %r12
	call	memset@PLT
	decq	%rbx
	je	.L756
	imulq	$736, %rbx, %rbx
	movq	%r12, %rcx
	addq	%r12, %rbx
	.p2align 4
	.p2align 3
.L757:
	movq	%rcx, %rdi
	movl	$736, %edx
	movq	%r15, %rsi
	call	memcpy@PLT
	movq	%rax, %rcx
	addq	$736, %rcx
	cmpq	%rcx, %rbx
	jne	.L757
	subq	%r15, %rbx
	movabsq	$250635109697140647, %rdx
	leaq	-1472(%rbx), %rax
	shrq	$5, %rax
	imulq	%rdx, %rax
	movabsq	$576460752303423487, %rdx
	andq	%rdx, %rax
	incq	%rax
	imulq	$736, %rax, %rax
	addq	%rax, %r12
.L756:
	movq	%r12, 8(%rbp)
	addq	$40, %rsp
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L787:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L793:
	.cfi_def_cfa_offset 96
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	movq	16(%rsp), %rdx
	movq	8(%rsp), %rdi
	movq	%r14, %rsi
	call	memmove@PLT
	movq	16(%rbp), %rsi
	subq	%r14, %rsi
.L768:
	movl	$32, %edx
	movq	%r14, %rdi
	call	_ZdlPvmSt11align_val_t@PLT
	jmp	.L769
	.p2align 4
	.p2align 3
.L794:
	movq	16(%rbp), %rsi
	subq	%r14, %rsi
	jmp	.L768
.L792:
	movabsq	$12531755484857032, %rdx
	cmpq	%rdx, %rax
	cmova	%rdx, %rax
	imulq	$736, %rax, %r15
.L761:
	movq	%r15, %rdi
	movl	$32, %esi
	call	_ZnwmSt11align_val_t@PLT
	movq	0(%rbp), %r14
	addq	%rax, %r15
	movq	%rax, 8(%rsp)
	movq	8(%rbp), %rax
	movq	%r15, 24(%rsp)
	subq	%r14, %rax
	movq	%rax, 16(%rsp)
	jmp	.L762
.L760:
	movabsq	$9223372036854775552, %r15
	jmp	.L761
.L791:
	leaq	.LC10(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7110:
	.size	_ZNSt6vectorI7ChannelSaIS0_EE17_M_default_appendEm, .-_ZNSt6vectorI7ChannelSaIS0_EE17_M_default_appendEm
	.section	.rodata._ZNSt6vectorIjSaIjEE14_M_fill_assignEmRKj.str1.8,"aMS",@progbits,1
	.align 8
.LC11:
	.string	"cannot create std::vector larger than max_size()"
	.section	.text._ZNSt6vectorIjSaIjEE14_M_fill_assignEmRKj,"axG",@progbits,_ZNSt6vectorIjSaIjEE14_M_fill_assignEmRKj,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorIjSaIjEE14_M_fill_assignEmRKj
	.type	_ZNSt6vectorIjSaIjEE14_M_fill_assignEmRKj, @function
_ZNSt6vectorIjSaIjEE14_M_fill_assignEmRKj:
.LFB7120:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsi, %rax
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	.cfi_offset 13, -24
	.cfi_offset 12, -32
	.cfi_offset 3, -40
	movq	%rdi, %rbx
	movq	(%rdi), %rdi
	movq	%rdx, %r12
	andq	$-64, %rsp
	movq	16(%rbx), %rsi
	subq	%rdi, %rsi
	movq	%rsi, %rdx
	sarq	$2, %rdx
	cmpq	%rax, %rdx
	jb	.L851
	movq	8(%rbx), %rcx
	movq	%rcx, %r8
	subq	%rdi, %r8
	sarq	$2, %r8
	cmpq	%r8, %rax
	jbe	.L807
	movl	(%r12), %esi
	cmpq	%rcx, %rdi
	je	.L808
	leaq	-4(%rcx), %r9
	movq	%rdi, %rdx
	subq	%rdi, %r9
	movq	%r9, %r10
	shrq	$2, %r10
	leaq	1(%r10), %r11
	cmpq	$56, %r9
	jbe	.L830
	movq	%r11, %r9
	vpbroadcastd	%esi, %zmm0
	shrq	$4, %r9
	salq	$6, %r9
	addq	%rdi, %r9
	.p2align 4
	.p2align 3
.L810:
	vmovdqu32	%zmm0, (%rdx)
	addq	$64, %rdx
	cmpq	%rdx, %r9
	jne	.L810
	movq	%r11, %r9
	andq	$-16, %r9
	leaq	(%rdi,%r9,4), %rdx
	cmpq	%r9, %r11
	je	.L811
.L809:
	subq	%r9, %r10
	leaq	1(%r10), %r11
	cmpq	$6, %r10
	jbe	.L812
	vpbroadcastd	%esi, %ymm0
	vmovdqu	%ymm0, (%rdi,%r9,4)
	movq	%r11, %rdi
	andq	$-8, %rdi
	leaq	(%rdx,%rdi,4), %rdx
	cmpq	%rdi, %r11
	je	.L811
.L812:
	leaq	4(%rdx), %rdi
	movl	%esi, (%rdx)
	cmpq	%rdi, %rcx
	je	.L811
	leaq	8(%rdx), %rdi
	movl	%esi, 4(%rdx)
	cmpq	%rdi, %rcx
	je	.L811
	leaq	12(%rdx), %rdi
	movl	%esi, 8(%rdx)
	cmpq	%rdi, %rcx
	je	.L811
	leaq	16(%rdx), %rdi
	movl	%esi, 12(%rdx)
	cmpq	%rdi, %rcx
	je	.L811
	leaq	20(%rdx), %rdi
	movl	%esi, 16(%rdx)
	cmpq	%rdi, %rcx
	je	.L811
	leaq	24(%rdx), %rdi
	movl	%esi, 20(%rdx)
	cmpq	%rdi, %rcx
	je	.L811
	movl	%esi, 24(%rdx)
.L811:
	movl	(%r12), %esi
.L808:
	subq	%r8, %rax
	salq	$2, %rax
	leaq	(%rcx,%rax), %rdi
	cmpq	%rdi, %rcx
	je	.L818
	subq	$4, %rax
	movq	%rcx, %rdx
	movq	%rax, %r8
	shrq	$2, %r8
	leaq	1(%r8), %r9
	cmpq	$56, %rax
	jbe	.L831
	movq	%r9, %rax
	vpbroadcastd	%esi, %zmm0
	shrq	$4, %rax
	salq	$6, %rax
	addq	%rcx, %rax
	.p2align 4
	.p2align 3
.L816:
	vmovdqu32	%zmm0, (%rdx)
	addq	$64, %rdx
	cmpq	%rax, %rdx
	jne	.L816
	movq	%r9, %rdx
	andq	$-16, %rdx
	leaq	(%rcx,%rdx,4), %rax
	cmpq	%rdx, %r9
	je	.L818
.L815:
	subq	%rdx, %r8
	leaq	1(%r8), %r9
	cmpq	$6, %r8
	jbe	.L820
	vpbroadcastd	%esi, %ymm0
	vmovdqu	%ymm0, (%rcx,%rdx,4)
	movq	%r9, %rdx
	andq	$-8, %rdx
	leaq	(%rax,%rdx,4), %rax
	cmpq	%rdx, %r9
	je	.L818
.L820:
	leaq	4(%rax), %rdx
	movl	%esi, (%rax)
	cmpq	%rdx, %rdi
	je	.L818
	leaq	8(%rax), %rdx
	movl	%esi, 4(%rax)
	cmpq	%rdx, %rdi
	je	.L818
	leaq	12(%rax), %rdx
	movl	%esi, 8(%rax)
	cmpq	%rdx, %rdi
	je	.L818
	leaq	16(%rax), %rdx
	movl	%esi, 12(%rax)
	cmpq	%rdx, %rdi
	je	.L818
	leaq	20(%rax), %rdx
	movl	%esi, 16(%rax)
	cmpq	%rdx, %rdi
	je	.L818
	leaq	24(%rax), %rdx
	movl	%esi, 20(%rax)
	cmpq	%rdx, %rdi
	je	.L818
	movl	%esi, 24(%rax)
.L818:
	movq	%rdi, 8(%rbx)
	vzeroupper
	leaq	-24(%rbp), %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
	.p2align 4
	.p2align 3
.L807:
	.cfi_restore_state
	movq	%rdi, %rsi
	testq	%rax, %rax
	je	.L822
	salq	$2, %rax
	movl	(%r12), %r8d
	leaq	(%rdi,%rax), %rsi
	cmpq	%rsi, %rdi
	je	.L822
	subq	$4, %rax
	movq	%rdi, %rdx
	movq	%rax, %r9
	shrq	$2, %r9
	leaq	1(%r9), %r10
	cmpq	$56, %rax
	jbe	.L833
	movq	%r10, %rax
	vpbroadcastd	%r8d, %zmm0
	shrq	$4, %rax
	salq	$6, %rax
	addq	%rdi, %rax
	.p2align 4
	.p2align 3
.L824:
	vmovdqu32	%zmm0, (%rdx)
	addq	$64, %rdx
	cmpq	%rdx, %rax
	jne	.L824
	movq	%r10, %rdx
	andq	$-16, %rdx
	leaq	(%rdi,%rdx,4), %rax
	cmpq	%rdx, %r10
	je	.L848
.L823:
	subq	%rdx, %r9
	leaq	1(%r9), %r10
	cmpq	$6, %r9
	jbe	.L826
	vpbroadcastd	%r8d, %ymm0
	vmovdqu	%ymm0, (%rdi,%rdx,4)
	movq	%r10, %rdx
	andq	$-8, %rdx
	leaq	(%rax,%rdx,4), %rax
	cmpq	%rdx, %r10
	je	.L848
.L826:
	leaq	4(%rax), %rdx
	movl	%r8d, (%rax)
	cmpq	%rdx, %rsi
	je	.L848
	leaq	8(%rax), %rdx
	movl	%r8d, 4(%rax)
	cmpq	%rdx, %rsi
	je	.L848
	leaq	12(%rax), %rdx
	movl	%r8d, 8(%rax)
	cmpq	%rdx, %rsi
	je	.L848
	leaq	16(%rax), %rdx
	movl	%r8d, 12(%rax)
	cmpq	%rdx, %rsi
	je	.L848
	leaq	20(%rax), %rdx
	movl	%r8d, 16(%rax)
	cmpq	%rdx, %rsi
	je	.L848
	leaq	24(%rax), %rdx
	movl	%r8d, 20(%rax)
	cmpq	%rdx, %rsi
	je	.L848
	movl	%r8d, 24(%rax)
	vzeroupper
.L822:
	cmpq	%rsi, %rcx
	je	.L849
	movq	%rsi, 8(%rbx)
.L849:
	leaq	-24(%rbp), %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
	.p2align 4
	.p2align 3
.L851:
	.cfi_restore_state
	movq	%rax, %rcx
	shrq	$61, %rcx
	jne	.L852
	leaq	0(,%rax,4), %r13
	testq	%rax, %rax
	je	.L828
	movq	%r13, %rdi
	call	_Znwm@PLT
	movl	(%r12), %edi
	leaq	(%rax,%r13), %rcx
	cmpq	%rax, %rcx
	je	.L799
	subq	$4, %r13
	movq	%rax, %rdx
	movq	%r13, %r8
	shrq	$2, %r8
	leaq	1(%r8), %r9
	cmpq	$56, %r13
	jbe	.L829
	movq	%r9, %rsi
	vpbroadcastd	%edi, %zmm0
	shrq	$4, %rsi
	salq	$6, %rsi
	addq	%rax, %rsi
	.p2align 4
	.p2align 3
.L801:
	vmovdqu32	%zmm0, (%rdx)
	addq	$64, %rdx
	cmpq	%rdx, %rsi
	jne	.L801
	movq	%r9, %rsi
	andq	$-16, %rsi
	leaq	(%rax,%rsi,4), %rdx
	cmpq	%r9, %rsi
	je	.L802
.L800:
	subq	%rsi, %r8
	leaq	1(%r8), %r9
	cmpq	$6, %r8
	jbe	.L803
	vpbroadcastd	%edi, %ymm0
	vmovdqu	%ymm0, (%rax,%rsi,4)
	movq	%r9, %rsi
	andq	$-8, %rsi
	leaq	(%rdx,%rsi,4), %rdx
	cmpq	%rsi, %r9
	je	.L802
.L803:
	leaq	4(%rdx), %rsi
	movl	%edi, (%rdx)
	cmpq	%rsi, %rcx
	je	.L802
	leaq	8(%rdx), %rsi
	movl	%edi, 4(%rdx)
	cmpq	%rsi, %rcx
	je	.L802
	leaq	12(%rdx), %rsi
	movl	%edi, 8(%rdx)
	cmpq	%rsi, %rcx
	je	.L802
	leaq	16(%rdx), %rsi
	movl	%edi, 12(%rdx)
	cmpq	%rsi, %rcx
	je	.L802
	leaq	20(%rdx), %rsi
	movl	%edi, 16(%rdx)
	cmpq	%rsi, %rcx
	je	.L802
	leaq	24(%rdx), %rsi
	movl	%edi, 20(%rdx)
	cmpq	%rsi, %rcx
	je	.L802
	movl	%edi, 24(%rdx)
.L802:
	movq	(%rbx), %rdi
	movq	16(%rbx), %rsi
	subq	%rdi, %rsi
	vzeroupper
.L798:
	vmovq	%rax, %xmm1
	movq	%rcx, 16(%rbx)
	vpinsrq	$1, %rcx, %xmm1, %xmm0
	vmovdqu	%xmm0, (%rbx)
	testq	%rdi, %rdi
	je	.L849
	leaq	-24(%rbp), %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	jmp	_ZdlPvm@PLT
	.p2align 4
	.p2align 3
.L828:
	.cfi_restore_state
	xorl	%eax, %eax
	xorl	%ecx, %ecx
	jmp	.L798
	.p2align 4
	.p2align 3
.L848:
	vzeroupper
	jmp	.L822
.L799:
	movq	(%rbx), %rdi
	movq	16(%rbx), %rsi
	subq	%rdi, %rsi
	jmp	.L798
.L830:
	xorl	%r9d, %r9d
	jmp	.L809
.L831:
	movq	%rcx, %rax
	xorl	%edx, %edx
	jmp	.L815
.L833:
	movq	%rdi, %rax
	xorl	%edx, %edx
	jmp	.L823
.L829:
	xorl	%esi, %esi
	jmp	.L800
.L852:
	leaq	.LC11(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7120:
	.size	_ZNSt6vectorIjSaIjEE14_M_fill_assignEmRKj, .-_ZNSt6vectorIjSaIjEE14_M_fill_assignEmRKj
	.section	.text._ZNSt6vectorI6ValuesSaIS0_EE17_M_default_appendEm,"axG",@progbits,_ZNSt6vectorI6ValuesSaIS0_EE17_M_default_appendEm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI6ValuesSaIS0_EE17_M_default_appendEm
	.type	_ZNSt6vectorI6ValuesSaIS0_EE17_M_default_appendEm, @function
_ZNSt6vectorI6ValuesSaIS0_EE17_M_default_appendEm:
.LFB7122:
	.cfi_startproc
	endbr64
	testq	%rsi, %rsi
	je	.L887
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movabsq	$144115188075855871, %rcx
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rdi, %r12
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %rdx
	movq	(%rdi), %r15
	movq	%rsi, %rbx
	movq	16(%rdi), %rax
	movq	%rdx, %rbp
	subq	%r15, %rbp
	subq	%rdx, %rax
	movq	%rbp, %r14
	sarq	$6, %rax
	sarq	$6, %r14
	subq	%r14, %rcx
	cmpq	%rax, %rsi
	jbe	.L890
	cmpq	%rsi, %rcx
	jb	.L891
	cmpq	%r14, %rsi
	movq	%r14, %r13
	cmovnb	%rsi, %r13
	addq	%r14, %r13
	jc	.L860
	testq	%r13, %r13
	jne	.L892
	movq	%rbp, %r8
	xorl	%r13d, %r13d
	xorl	%ecx, %ecx
.L862:
	movq	%rbx, %rsi
	addq	%rcx, %rbp
	vpxor	%xmm0, %xmm0, %xmm0
	decq	%rsi
	vmovdqa	%xmm0, 0(%rbp)
	vmovdqa	%xmm0, 16(%rbp)
	vmovdqa	%xmm0, 32(%rbp)
	vmovdqa	%xmm0, 48(%rbp)
	je	.L867
	salq	$6, %rsi
	leaq	64(%rbp), %rax
	leaq	64(%rbp,%rsi), %rsi
	.p2align 4
	.p2align 3
.L866:
	vmovdqa	0(%rbp), %xmm6
	addq	$64, %rax
	vmovdqa	%xmm6, -64(%rax)
	vmovdqa	16(%rbp), %xmm7
	vmovdqa	%xmm7, -48(%rax)
	vmovdqa	32(%rbp), %xmm1
	vmovdqa	%xmm1, -32(%rax)
	vmovdqa	48(%rbp), %xmm6
	vmovdqa	%xmm6, -16(%rax)
	cmpq	%rax, %rsi
	jne	.L866
.L867:
	testq	%r8, %r8
	jg	.L893
	testq	%r15, %r15
	jne	.L894
.L869:
	addq	%r14, %rbx
	vmovq	%rcx, %xmm1
	movq	%r13, 16(%r12)
	salq	$6, %rbx
	addq	%rcx, %rbx
	vpinsrq	$1, %rbx, %xmm1, %xmm0
	vmovdqu	%xmm0, (%r12)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L890:
	.cfi_restore_state
	vpxor	%xmm0, %xmm0, %xmm0
	decq	%rbx
	leaq	64(%rdx), %rcx
	vmovdqa	%xmm0, (%rdx)
	vmovdqa	%xmm0, 16(%rdx)
	vmovdqa	%xmm0, 32(%rdx)
	vmovdqa	%xmm0, 48(%rdx)
	je	.L856
	salq	$6, %rbx
	movq	%rcx, %rax
	addq	%rcx, %rbx
	.p2align 4
	.p2align 3
.L857:
	vmovdqa	(%rdx), %xmm2
	addq	$64, %rax
	vmovdqa	%xmm2, -64(%rax)
	vmovdqa	16(%rdx), %xmm3
	vmovdqa	%xmm3, -48(%rax)
	vmovdqa	32(%rdx), %xmm4
	vmovdqa	%xmm4, -32(%rax)
	vmovdqa	48(%rdx), %xmm5
	vmovdqa	%xmm5, -16(%rax)
	cmpq	%rax, %rbx
	jne	.L857
	subq	%rdx, %rbx
	leaq	-64(%rcx,%rbx), %rcx
.L856:
	movq	%rcx, 8(%r12)
	addq	$24, %rsp
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L887:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L893:
	.cfi_def_cfa_offset 80
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	movq	%r15, %rsi
	movq	%rcx, %rdi
	movq	%r8, %rdx
	call	memmove@PLT
	movq	16(%r12), %rsi
	movq	%rax, %rcx
	subq	%r15, %rsi
.L868:
	movl	$32, %edx
	movq	%r15, %rdi
	movq	%rcx, 8(%rsp)
	call	_ZdlPvmSt11align_val_t@PLT
	movq	8(%rsp), %rcx
	jmp	.L869
	.p2align 4
	.p2align 3
.L894:
	movq	16(%r12), %rsi
	subq	%r15, %rsi
	jmp	.L868
.L892:
	movabsq	$144115188075855871, %rax
	cmpq	%rax, %r13
	cmova	%rax, %r13
	salq	$6, %r13
.L861:
	movq	%r13, %rdi
	movl	$32, %esi
	call	_ZnwmSt11align_val_t@PLT
	movq	(%r12), %r15
	movq	8(%r12), %r8
	movq	%rax, %rcx
	addq	%rax, %r13
	subq	%r15, %r8
	jmp	.L862
.L860:
	movabsq	$9223372036854775744, %r13
	jmp	.L861
.L891:
	leaq	.LC10(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7122:
	.size	_ZNSt6vectorI6ValuesSaIS0_EE17_M_default_appendEm, .-_ZNSt6vectorI6ValuesSaIS0_EE17_M_default_appendEm
	.section	.text._ZNSt6vectorI5StateSaIS0_EE17_M_default_appendEm,"axG",@progbits,_ZNSt6vectorI5StateSaIS0_EE17_M_default_appendEm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI5StateSaIS0_EE17_M_default_appendEm
	.type	_ZNSt6vectorI5StateSaIS0_EE17_M_default_appendEm, @function
_ZNSt6vectorI5StateSaIS0_EE17_M_default_appendEm:
.LFB7173:
	.cfi_startproc
	endbr64
	testq	%rsi, %rsi
	je	.L929
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movabsq	$576460752303423487, %rcx
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rdi, %rbp
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %rdx
	movq	(%rdi), %r15
	movq	%rsi, %rbx
	movq	16(%rdi), %rax
	movq	%rdx, %r12
	subq	%r15, %r12
	subq	%rdx, %rax
	movq	%r12, %r14
	sarq	$4, %rax
	sarq	$4, %r14
	subq	%r14, %rcx
	cmpq	%rax, %rsi
	jbe	.L932
	cmpq	%rsi, %rcx
	jb	.L933
	cmpq	%r14, %rsi
	movq	%r14, %r13
	cmovnb	%rsi, %r13
	addq	%r14, %r13
	jc	.L902
	testq	%r13, %r13
	jne	.L934
	movq	%r12, %r8
	xorl	%r13d, %r13d
	xorl	%ecx, %ecx
.L904:
	movq	%rbx, %rsi
	addq	%rcx, %r12
	decq	%rsi
	movq	$0x000000000, (%r12)
	movq	$0, 8(%r12)
	je	.L909
	salq	$4, %rsi
	leaq	16(%r12), %rax
	leaq	16(%r12,%rsi), %rsi
	.p2align 4
	.p2align 3
.L908:
	vmovdqu	(%r12), %xmm3
	addq	$16, %rax
	vmovdqu	%xmm3, -16(%rax)
	cmpq	%rax, %rsi
	jne	.L908
.L909:
	testq	%r8, %r8
	jg	.L935
	testq	%r15, %r15
	jne	.L936
.L911:
	addq	%r14, %rbx
	vmovq	%rcx, %xmm1
	movq	%r13, 16(%rbp)
	salq	$4, %rbx
	addq	%rcx, %rbx
	vpinsrq	$1, %rbx, %xmm1, %xmm0
	vmovdqu	%xmm0, 0(%rbp)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L932:
	.cfi_restore_state
	decq	%rbx
	movq	$0x000000000, (%rdx)
	movq	$0, 8(%rdx)
	leaq	16(%rdx), %rcx
	je	.L898
	salq	$4, %rbx
	movq	%rcx, %rax
	addq	%rcx, %rbx
	.p2align 4
	.p2align 3
.L899:
	vmovdqu	(%rdx), %xmm2
	addq	$16, %rax
	vmovdqu	%xmm2, -16(%rax)
	cmpq	%rax, %rbx
	jne	.L899
	subq	%rdx, %rbx
	leaq	-16(%rcx,%rbx), %rcx
.L898:
	movq	%rcx, 8(%rbp)
	addq	$24, %rsp
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L929:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L935:
	.cfi_def_cfa_offset 80
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	movq	%r15, %rsi
	movq	%rcx, %rdi
	movq	%r8, %rdx
	call	memmove@PLT
	movq	16(%rbp), %rsi
	movq	%rax, %rcx
	subq	%r15, %rsi
.L910:
	movq	%r15, %rdi
	movq	%rcx, 8(%rsp)
	call	_ZdlPvm@PLT
	movq	8(%rsp), %rcx
	jmp	.L911
	.p2align 4
	.p2align 3
.L936:
	movq	16(%rbp), %rsi
	subq	%r15, %rsi
	jmp	.L910
.L934:
	movabsq	$576460752303423487, %rax
	cmpq	%rax, %r13
	cmova	%rax, %r13
	salq	$4, %r13
.L903:
	movq	%r13, %rdi
	call	_Znwm@PLT
	movq	0(%rbp), %r15
	movq	8(%rbp), %r8
	movq	%rax, %rcx
	addq	%rax, %r13
	subq	%r15, %r8
	jmp	.L904
.L902:
	movabsq	$9223372036854775792, %r13
	jmp	.L903
.L933:
	leaq	.LC10(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7173:
	.size	_ZNSt6vectorI5StateSaIS0_EE17_M_default_appendEm, .-_ZNSt6vectorI5StateSaIS0_EE17_M_default_appendEm
	.section	.text._ZNSt6vectorIZN9Optimizer14informed_seedsEvE10ConstraintSaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,"axG",@progbits,_ZNSt6vectorIZN9Optimizer14informed_seedsEvE10ConstraintSaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorIZN9Optimizer14informed_seedsEvE10ConstraintSaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.type	_ZNSt6vectorIZN9Optimizer14informed_seedsEvE10ConstraintSaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, @function
_ZNSt6vectorIZN9Optimizer14informed_seedsEvE10ConstraintSaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_:
.LFB7258:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rdx, %rbx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %r15
	movq	(%rdi), %r13
	movabsq	$-8198552921648689607, %rdx
	movq	%r15, %rax
	subq	%r13, %rax
	sarq	$3, %rax
	imulq	%rdx, %rax
	movabsq	$128102389400760775, %rdx
	cmpq	%rdx, %rax
	je	.L958
	testq	%rax, %rax
	movl	$1, %edx
	movq	%rdi, %rbp
	movq	%rsi, %r12
	cmovne	%rax, %rdx
	xorl	%ecx, %ecx
	addq	%rdx, %rax
	movq	%rsi, %rdx
	setc	%cl
	subq	%r13, %rdx
	testq	%rcx, %rcx
	jne	.L950
	testq	%rax, %rax
	jne	.L942
	xorl	%r14d, %r14d
	xorl	%edi, %edi
.L948:
	vmovdqu	(%rbx), %xmm2
	vmovdqu	16(%rbx), %xmm3
	subq	%r12, %r15
	vmovq	%rdi, %xmm1
	vmovdqu	32(%rbx), %xmm4
	vmovdqu	48(%rbx), %xmm5
	movq	64(%rbx), %rax
	leaq	72(%rdi,%rdx), %rbx
	movq	%rax, 64(%rdi,%rdx)
	leaq	(%rbx,%r15), %rax
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqu	%xmm2, (%rdi,%rdx)
	vmovdqu	%xmm3, 16(%rdi,%rdx)
	vmovdqa	%xmm0, (%rsp)
	vmovdqu	%xmm4, 32(%rdi,%rdx)
	vmovdqu	%xmm5, 48(%rdi,%rdx)
	testq	%rdx, %rdx
	jg	.L959
	testq	%r15, %r15
	jg	.L946
	testq	%r13, %r13
	jne	.L957
.L947:
	vmovdqa	(%rsp), %xmm6
	movq	%r14, 16(%rbp)
	vmovdqu	%xmm6, 0(%rbp)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L959:
	.cfi_restore_state
	movq	%r13, %rsi
	call	memmove@PLT
	testq	%r15, %r15
	jg	.L946
.L957:
	movq	16(%rbp), %rsi
	movq	%r13, %rdi
	subq	%r13, %rsi
	call	_ZdlPvm@PLT
	jmp	.L947
	.p2align 4
	.p2align 3
.L946:
	movq	%r15, %rdx
	movq	%r12, %rsi
	movq	%rbx, %rdi
	call	memcpy@PLT
	testq	%r13, %r13
	je	.L947
	jmp	.L957
	.p2align 4
	.p2align 3
.L950:
	movabsq	$9223372036854775800, %r14
.L941:
	movq	%r14, %rdi
	movq	%rdx, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rdx
	addq	%rax, %r14
	jmp	.L948
	.p2align 4
	.p2align 3
.L942:
	movabsq	$128102389400760775, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	leaq	(%rax,%rax,8), %r14
	salq	$3, %r14
	jmp	.L941
.L958:
	leaq	.LC0(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7258:
	.size	_ZNSt6vectorIZN9Optimizer14informed_seedsEvE10ConstraintSaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, .-_ZNSt6vectorIZN9Optimizer14informed_seedsEvE10ConstraintSaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.section	.text._ZNSt6vectorI5StateSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_,"axG",@progbits,_ZNSt6vectorI5StateSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI5StateSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
	.type	_ZNSt6vectorI5StateSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_, @function
_ZNSt6vectorI5StateSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_:
.LFB7298:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movq	%rdx, %r15
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movabsq	$576460752303423487, %rdx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %r12
	movq	(%rdi), %r14
	movq	%r12, %rax
	subq	%r14, %rax
	sarq	$4, %rax
	cmpq	%rdx, %rax
	je	.L981
	testq	%rax, %rax
	movl	$1, %edx
	movq	%rdi, %rbp
	movq	%rsi, %r13
	cmovne	%rax, %rdx
	xorl	%ecx, %ecx
	addq	%rdx, %rax
	movq	%rsi, %rdx
	setc	%cl
	subq	%r14, %rdx
	testq	%rcx, %rcx
	jne	.L973
	testq	%rax, %rax
	jne	.L965
	xorl	%ebx, %ebx
	xorl	%edi, %edi
.L971:
	vmovdqu	(%r15), %xmm2
	subq	%r13, %r12
	leaq	16(%rdi,%rdx), %r15
	vmovq	%rdi, %xmm1
	leaq	(%r15,%r12), %rax
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqa	%xmm0, (%rsp)
	vmovdqu	%xmm2, (%rdi,%rdx)
	testq	%rdx, %rdx
	jg	.L982
	testq	%r12, %r12
	jg	.L969
	testq	%r14, %r14
	jne	.L980
.L970:
	vmovdqa	(%rsp), %xmm3
	movq	%rbx, 16(%rbp)
	vmovdqu	%xmm3, 0(%rbp)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L982:
	.cfi_restore_state
	movq	%r14, %rsi
	call	memmove@PLT
	testq	%r12, %r12
	jg	.L969
.L980:
	movq	16(%rbp), %rsi
	movq	%r14, %rdi
	subq	%r14, %rsi
	call	_ZdlPvm@PLT
	jmp	.L970
	.p2align 4
	.p2align 3
.L969:
	movq	%r12, %rdx
	movq	%r13, %rsi
	movq	%r15, %rdi
	call	memcpy@PLT
	testq	%r14, %r14
	je	.L970
	jmp	.L980
	.p2align 4
	.p2align 3
.L973:
	movabsq	$9223372036854775792, %rbx
.L964:
	movq	%rbx, %rdi
	movq	%rdx, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rdx
	addq	%rax, %rbx
	jmp	.L971
	.p2align 4
	.p2align 3
.L965:
	movabsq	$576460752303423487, %rbx
	cmpq	%rbx, %rax
	cmovbe	%rax, %rbx
	salq	$4, %rbx
	jmp	.L964
.L981:
	leaq	.LC0(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7298:
	.size	_ZNSt6vectorI5StateSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_, .-_ZNSt6vectorI5StateSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
	.section	.text._ZNSt6vectorI5StateSaIS0_EE9push_backERKS0_,"axG",@progbits,_ZNSt6vectorI5StateSaIS0_EE9push_backERKS0_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI5StateSaIS0_EE9push_backERKS0_
	.type	_ZNSt6vectorI5StateSaIS0_EE9push_backERKS0_, @function
_ZNSt6vectorI5StateSaIS0_EE9push_backERKS0_:
.LFB6795:
	.cfi_startproc
	endbr64
	movq	8(%rdi), %r8
	cmpq	16(%rdi), %r8
	je	.L984
	vmovdqu	(%rsi), %xmm0
	addq	$16, %r8
	vmovdqu	%xmm0, -16(%r8)
	movq	%r8, 8(%rdi)
	ret
	.p2align 4
	.p2align 3
.L984:
	movq	%rsi, %rdx
	movq	%r8, %rsi
	jmp	_ZNSt6vectorI5StateSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
	.cfi_endproc
.LFE6795:
	.size	_ZNSt6vectorI5StateSaIS0_EE9push_backERKS0_, .-_ZNSt6vectorI5StateSaIS0_EE9push_backERKS0_
	.section	.text._ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv,"axG",@progbits,_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	.type	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv, @function
_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv:
.LFB7352:
	.cfi_startproc
	endbr64
	vpbroadcastq	.LC20(%rip), %zmm3
	vpbroadcastq	.LC21(%rip), %zmm4
	movq	%rdi, %rcx
	leaq	1248(%rdi), %rax
	vpbroadcastq	.LC22(%rip), %zmm5
	vpbroadcastq	.LC23(%rip), %zmm6
	leaq	1216(%rdi), %rsi
	movq	%rdi, %rdx
	.p2align 4
	.p2align 3
.L989:
	vpandq	8(%rdx), %zmm4, %zmm1
	vpandq	(%rdx), %zmm3, %zmm0
	addq	$64, %rdx
	vporq	%zmm1, %zmm0, %zmm0
	vpsrlq	$1, %zmm0, %zmm1
	vpxorq	1184(%rdx), %zmm1, %zmm1
	vpandq	%zmm5, %zmm0, %zmm0
	vptestnmq	%zmm0, %zmm0, %k1
	vpxorq	%zmm6, %zmm1, %zmm2
	vpblendmq	%zmm1, %zmm2, %zmm0{%k1}
	vmovdqu64	%zmm0, -64(%rdx)
	cmpq	%rdx, %rsi
	jne	.L989
	vpbroadcastq	.LC20(%rip), %ymm0
	vpbroadcastq	.LC21(%rip), %ymm1
	leaq	2464(%rcx), %rdx
	vpand	1224(%rcx), %ymm1, %ymm1
	vpand	1216(%rcx), %ymm0, %ymm0
	vpor	%ymm1, %ymm0, %ymm0
	vpsrlq	$1, %ymm0, %ymm1
	vpxor	2464(%rcx), %ymm1, %ymm1
	vpandq	.LC22(%rip){1to4}, %ymm0, %ymm0
	vptestnmq	%ymm0, %ymm0, %k1
	vpxorq	.LC23(%rip){1to4}, %ymm1, %ymm2
	vpblendmq	%ymm1, %ymm2, %ymm0{%k1}
	vmovdqu	%ymm0, 1216(%rcx)
	.p2align 4
	.p2align 3
.L990:
	vpandq	8(%rax), %zmm4, %zmm1
	addq	$64, %rax
	vpandq	-64(%rax), %zmm3, %zmm0
	vporq	%zmm1, %zmm0, %zmm0
	vpsrlq	$1, %zmm0, %zmm1
	vpxorq	-1312(%rax), %zmm1, %zmm1
	vpandq	%zmm5, %zmm0, %zmm0
	vptestnmq	%zmm0, %zmm0, %k1
	vpxorq	%zmm6, %zmm1, %zmm2
	vpblendmq	%zmm1, %zmm2, %zmm0{%k1}
	vmovdqu64	%zmm0, -64(%rax)
	cmpq	%rdx, %rax
	jne	.L990
	movq	2472(%rcx), %rdx
	movq	2464(%rcx), %rax
	movq	%rdx, %rsi
	andq	$-2147483648, %rax
	andl	$2147483647, %esi
	orq	%rsi, %rax
	movq	%rax, %rsi
	shrq	%rsi
	xorq	1216(%rcx), %rsi
	testb	$1, %al
	je	.L991
	movabsq	$-5403634167711393303, %rax
	xorq	%rax, %rsi
.L991:
	movq	2480(%rcx), %rax
	movq	%rsi, 2464(%rcx)
	andq	$-2147483648, %rdx
	movq	%rax, %rsi
	andl	$2147483647, %esi
	orq	%rsi, %rdx
	movq	%rdx, %rsi
	shrq	%rsi
	xorq	1224(%rcx), %rsi
	andl	$1, %edx
	je	.L992
	movabsq	$-5403634167711393303, %rdx
	xorq	%rdx, %rsi
.L992:
	movq	%rsi, 2472(%rcx)
	movq	2488(%rcx), %rsi
	andq	$-2147483648, %rax
	movq	%rsi, %rdx
	andl	$2147483647, %edx
	orq	%rdx, %rax
	movq	%rax, %rdx
	shrq	%rdx
	xorq	1232(%rcx), %rdx
	testb	$1, %al
	jne	.L993
.L996:
	movq	(%rcx), %rax
	andq	$-2147483648, %rsi
	movq	%rdx, 2480(%rcx)
	andl	$2147483647, %eax
	orq	%rsi, %rax
	movq	%rax, %rdx
	shrq	%rdx
	xorq	1240(%rcx), %rdx
	testb	$1, %al
	je	.L995
	movabsq	$-5403634167711393303, %rax
	xorq	%rax, %rdx
.L995:
	movq	%rdx, 2488(%rcx)
	movq	$0, 2496(%rcx)
	vzeroupper
	ret
.L993:
	movabsq	$-5403634167711393303, %rax
	xorq	%rax, %rdx
	jmp	.L996
	.cfi_endproc
.LFE7352:
	.size	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv, .-_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	.section	.text._ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEclEv,"axG",@progbits,_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEclEv,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEclEv
	.type	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEclEv, @function
_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEclEv:
.LFB6848:
	.cfi_startproc
	endbr64
	movq	2496(%rdi), %rax
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset 3, -16
	movq	%rdi, %rbx
	cmpq	$311, %rax
	ja	.L1008
.L1006:
	leaq	1(%rax), %rdx
	movq	(%rbx,%rax,8), %rax
	movabsq	$6148914691236517205, %rcx
	movq	%rdx, 2496(%rbx)
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 8
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%rcx, %rdx
	movabsq	$8202884508482404352, %rcx
	xorq	%rax, %rdx
	movq	%rdx, %rax
	salq	$17, %rax
	andq	%rcx, %rax
	movabsq	$-2270628950310912, %rcx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rcx, %rdx
	xorq	%rax, %rdx
	movq	%rdx, %rax
	shrq	$43, %rax
	xorq	%rdx, %rax
	ret
	.p2align 4
	.p2align 3
.L1008:
	.cfi_restore_state
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rax
	jmp	.L1006
	.cfi_endproc
.LFE6848:
	.size	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEclEv, .-_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEclEv
	.section	.text._ZN9Optimizer7perturbEmi,"axG",@progbits,_ZN9Optimizer7perturbEmi,comdat
	.align 2
	.p2align 4
	.weak	_ZN9Optimizer7perturbEmi
	.type	_ZN9Optimizer7perturbEmi, @function
_ZN9Optimizer7perturbEmi:
.LFB6134:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movq	%rdi, %r13
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rsi, %rbx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	testl	%edx, %edx
	jle	.L1020
	leaq	296(%rdi), %rax
	movq	2792(%rdi), %rdi
	movl	%edx, %r15d
	movq	%rsi, %r14
	movq	%rax, 8(%rsp)
	xorl	%r12d, %r12d
	movabsq	$6148914691236517205, %r9
	movabsq	$8202884508482404352, %r8
	movabsq	$-2270628950310912, %rbp
	.p2align 4
	.p2align 3
.L1014:
	movq	%rdi, %rax
	cmpq	$311, %rdi
	ja	.L1026
.L1011:
	leaq	1(%rax), %rdi
	movq	296(%r13,%rax,8), %rax
	popcntq	%r14, %rcx
	movq	%rdi, 2792(%r13)
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%r9, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%r8, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rbp, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	%rcx
	movq	%r14, %rax
	leal	-1(%rdx), %ecx
	testq	%rdx, %rdx
	je	.L1012
	.p2align 4
	.p2align 3
.L1013:
	blsr	%rax, %rax
	subl	$1, %ecx
	jnb	.L1013
.L1012:
	blsi	%rax, %rax
	incl	%r12d
	xorq	%rax, %r14
	cmpl	%r12d, %r15d
	jne	.L1014
.L1010:
	movl	8(%r13), %r15d
	popcntq	%r14, %rax
	cmpl	%eax, %r15d
	jle	.L1009
	leaq	296(%r13), %rax
	movabsq	$6148914691236517205, %r8
	movabsq	$8202884508482404352, %r12
	movabsq	$-2270628950310912, %rbp
	movq	%rax, 8(%rsp)
	movq	2792(%r13), %rax
	jmp	.L1019
	.p2align 4
	.p2align 3
.L1028:
	movl	$1, %eax
	shlx	%rdx, %rax, %rdx
	orq	%rdx, %r14
	popcntq	%r14, %rax
	cmpl	%eax, %r15d
	jle	.L1009
.L1018:
	movq	%r9, %rax
.L1019:
	cmpq	$311, %rax
	ja	.L1027
.L1016:
	leaq	1(%rax), %r9
	movq	296(%r13,%rax,8), %rax
	movslq	4(%r13), %rdi
	movq	%r9, 2792(%r13)
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%r8, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%r12, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rbp, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	%rdi
	btq	%rdx, %rbx
	jnc	.L1028
	popcntq	%r14, %rax
	cmpl	%r15d, %eax
	jl	.L1018
.L1009:
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	movq	%r14, %rax
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1026:
	.cfi_restore_state
	movq	8(%rsp), %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2792(%r13), %rax
	movabsq	$8202884508482404352, %r8
	movabsq	$6148914691236517205, %r9
	jmp	.L1011
	.p2align 4
	.p2align 3
.L1027:
	movq	8(%rsp), %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2792(%r13), %rax
	movabsq	$6148914691236517205, %r8
	jmp	.L1016
.L1020:
	movq	%rsi, %r14
	jmp	.L1010
	.cfi_endproc
.LFE6134:
	.size	_ZN9Optimizer7perturbEmi, .-_ZN9Optimizer7perturbEmi
	.section	.text._ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPiSt6vectorIiSaIiEEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SA_OT0_,"axG",@progbits,_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPiSt6vectorIiSaIiEEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SA_OT0_,comdat
	.p2align 4
	.weak	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPiSt6vectorIiSaIiEEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SA_OT0_
	.type	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPiSt6vectorIiSaIiEEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SA_OT0_, @function
_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPiSt6vectorIiSaIiEEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SA_OT0_:
.LFB6699:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	%rsi, (%rsp)
	cmpq	%rdi, %rsi
	je	.L1058
	movq	%rsi, %rcx
	movq	%rdx, %rbx
	movq	%rdi, %r14
	leaq	4(%rdi), %r12
	subq	%rdi, %rcx
	sarq	$2, %rcx
	movq	%rcx, %rax
	mulq	%rcx
	seto	%al
	movzbl	%al, %eax
	testq	%rax, %rax
	je	.L1060
	cmpq	(%rsp), %r12
	je	.L1058
	movabsq	$6148914691236517205, %r8
	movabsq	$8202884508482404352, %rbp
	movabsq	$-2270628950310912, %r15
	.p2align 4
	.p2align 3
.L1051:
	movq	2496(%rbx), %rdx
	movq	%r12, %rax
	subq	%r14, %rax
	sarq	$2, %rax
	movq	%rdx, %rsi
	cmpq	$-1, %rax
	je	.L1044
	leaq	1(%rax), %r13
	cmpq	$311, %rdx
	ja	.L1061
.L1045:
	movq	(%rbx,%rdx,8), %rsi
	leaq	1(%rdx), %r9
	movq	%r9, 2496(%rbx)
	movq	%rsi, %rdx
	shrq	$29, %rdx
	andq	%r8, %rdx
	xorq	%rdx, %rsi
	movq	%rsi, %rdx
	salq	$17, %rdx
	andq	%rbp, %rdx
	xorq	%rdx, %rsi
	movq	%rsi, %rdx
	salq	$37, %rdx
	andq	%r15, %rdx
	xorq	%rdx, %rsi
	movq	%rsi, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rsi
	movq	%rsi, %rdx
	mulx	%r13, %rsi, %rdi
	cmpq	%rsi, %r13
	jbe	.L1046
	notq	%rax
	xorl	%edx, %edx
	divq	%r13
	movq	%rdx, %rcx
	cmpq	%rdx, %rsi
	jb	.L1048
	jmp	.L1046
	.p2align 4
	.p2align 3
.L1047:
	movq	(%rbx,%rax,8), %rsi
	leaq	1(%rax), %r9
	movq	%r9, 2496(%rbx)
	movq	%rsi, %rax
	shrq	$29, %rax
	andq	%r8, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$17, %rax
	andq	%rbp, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$37, %rax
	andq	%r15, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	shrq	$43, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rdx
	mulx	%r13, %rsi, %rdi
	cmpq	%rsi, %rcx
	jbe	.L1046
.L1048:
	movq	%r9, %rax
	cmpq	$311, %r9
	jbe	.L1047
	movq	%rbx, %rdi
	movq	%rcx, 8(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$6148914691236517205, %r8
	movq	2496(%rbx), %rax
	movq	8(%rsp), %rcx
	jmp	.L1047
	.p2align 4
	.p2align 3
.L1046:
	movq	%rdi, %rax
.L1049:
	leaq	(%r14,%rax,4), %rax
	movl	(%r12), %edx
	addq	$4, %r12
	movl	(%rax), %esi
	movl	%esi, -4(%r12)
	movl	%edx, (%rax)
	cmpq	%r12, (%rsp)
	jne	.L1051
.L1058:
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1044:
	.cfi_restore_state
	cmpq	$311, %rdx
	ja	.L1062
.L1050:
	leaq	1(%rsi), %rax
	movq	%rax, 2496(%rbx)
	movq	(%rbx,%rsi,8), %rax
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%r8, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rbp, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%r15, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	jmp	.L1049
	.p2align 4
	.p2align 3
.L1061:
	movq	%rbx, %rdi
	movq	%rax, 8(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$6148914691236517205, %r8
	movq	2496(%rbx), %rdx
	movq	8(%rsp), %rax
	jmp	.L1045
	.p2align 4
	.p2align 3
.L1062:
	movq	%rbx, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rsi
	movabsq	$6148914691236517205, %r8
	jmp	.L1050
	.p2align 4
	.p2align 3
.L1060:
	andl	$1, %ecx
	je	.L1063
.L1034:
	cmpq	%r12, (%rsp)
	je	.L1058
	movabsq	$6148914691236517205, %r9
	movabsq	$8202884508482404352, %r8
	movabsq	$-2270628950310912, %rbp
	.p2align 4
	.p2align 3
.L1043:
	movq	%r12, %r13
	movq	2496(%rbx), %rax
	subq	%r14, %r13
	sarq	$2, %r13
	leaq	2(%r13), %r15
	incq	%r13
	imulq	%r15, %r13
	testq	%r13, %r13
	je	.L1036
	cmpq	$311, %rax
	ja	.L1064
.L1037:
	movq	(%rbx,%rax,8), %rsi
	leaq	1(%rax), %r11
	movq	%r11, 2496(%rbx)
	movq	%rsi, %rax
	shrq	$29, %rax
	andq	%r9, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$17, %rax
	andq	%r8, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$37, %rax
	andq	%rbp, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	shrq	$43, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rdx
	mulx	%r13, %rsi, %rdi
	cmpq	%rsi, %r13
	jbe	.L1038
	movq	%r13, %rax
	xorl	%edx, %edx
	negq	%rax
	divq	%r13
	movq	%rdx, %rcx
	cmpq	%rdx, %rsi
	jb	.L1040
	jmp	.L1038
	.p2align 4
	.p2align 3
.L1039:
	movq	(%rbx,%rax,8), %rsi
	leaq	1(%rax), %r11
	movq	%r11, 2496(%rbx)
	movq	%rsi, %rax
	shrq	$29, %rax
	andq	%r9, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$17, %rax
	andq	%r8, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$37, %rax
	andq	%rbp, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	shrq	$43, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rdx
	mulx	%r13, %rsi, %rdi
	cmpq	%rsi, %rcx
	jbe	.L1038
.L1040:
	movq	%r11, %rax
	cmpq	$311, %r11
	jbe	.L1039
	movq	%rbx, %rdi
	movq	%rcx, 8(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$8202884508482404352, %r8
	movabsq	$6148914691236517205, %r9
	movq	2496(%rbx), %rax
	movq	8(%rsp), %rcx
	jmp	.L1039
	.p2align 4
	.p2align 3
.L1038:
	movq	%rdi, %rax
.L1041:
	xorl	%edx, %edx
	movl	(%r12), %esi
	addq	$8, %r12
	divq	%r15
	leaq	(%r14,%rax,4), %rax
	movl	(%rax), %edi
	movl	%edi, -8(%r12)
	movl	%esi, (%rax)
	leaq	(%r14,%rdx,4), %rax
	movl	-4(%r12), %edx
	movl	(%rax), %esi
	movl	%esi, -4(%r12)
	movl	%edx, (%rax)
	cmpq	%r12, (%rsp)
	jne	.L1043
	jmp	.L1058
	.p2align 4
	.p2align 3
.L1036:
	cmpq	$311, %rax
	ja	.L1065
.L1042:
	leaq	1(%rax), %rdx
	movq	(%rbx,%rax,8), %rax
	movq	%rdx, 2496(%rbx)
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%r9, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%r8, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rbp, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	jmp	.L1041
	.p2align 4
	.p2align 3
.L1064:
	movq	%rbx, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rax
	movabsq	$8202884508482404352, %r8
	movabsq	$6148914691236517205, %r9
	jmp	.L1037
	.p2align 4
	.p2align 3
.L1065:
	movq	%rbx, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rax
	movabsq	$8202884508482404352, %r8
	movabsq	$6148914691236517205, %r9
	jmp	.L1042
.L1063:
	movq	2496(%rbx), %rax
	cmpq	$311, %rax
	ja	.L1066
.L1035:
	leaq	1(%rax), %rdx
	movq	(%rbx,%rax,8), %rax
	movabsq	$6148914691236517205, %rcx
	xorl	%edi, %edi
	movq	%rdx, 2496(%rbx)
	leaq	8(%r14), %r12
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%rcx, %rdx
	movabsq	$8202884508482404352, %rcx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rcx, %rdx
	movabsq	$-2270628950310912, %rcx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rcx, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	movl	4(%r14), %edx
	shldq	$1, %rax, %rdi
	leaq	(%r14,%rdi,4), %rax
	movl	(%rax), %ecx
	movl	%ecx, 4(%r14)
	movl	%edx, (%rax)
	jmp	.L1034
.L1066:
	movq	%rbx, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rax
	jmp	.L1035
	.cfi_endproc
.LFE6699:
	.size	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPiSt6vectorIiSaIiEEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SA_OT0_, .-_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPiSt6vectorIiSaIiEEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SA_OT0_
	.section	.text._ZNSt6vectorIiSaIiEE17_M_realloc_insertIJRKiEEEvN9__gnu_cxx17__normal_iteratorIPiS1_EEDpOT_,"axG",@progbits,_ZNSt6vectorIiSaIiEE17_M_realloc_insertIJRKiEEEvN9__gnu_cxx17__normal_iteratorIPiS1_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorIiSaIiEE17_M_realloc_insertIJRKiEEEvN9__gnu_cxx17__normal_iteratorIPiS1_EEDpOT_
	.type	_ZNSt6vectorIiSaIiEE17_M_realloc_insertIJRKiEEEvN9__gnu_cxx17__normal_iteratorIPiS1_EEDpOT_, @function
_ZNSt6vectorIiSaIiEE17_M_realloc_insertIJRKiEEEvN9__gnu_cxx17__normal_iteratorIPiS1_EEDpOT_:
.LFB7359:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movq	%rdx, %r15
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movabsq	$2305843009213693951, %rdx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %r12
	movq	(%rdi), %r14
	movq	%r12, %rax
	subq	%r14, %rax
	sarq	$2, %rax
	cmpq	%rdx, %rax
	je	.L1088
	testq	%rax, %rax
	movl	$1, %edx
	movq	%rdi, %rbp
	movq	%rsi, %r13
	cmovne	%rax, %rdx
	xorl	%ecx, %ecx
	addq	%rdx, %rax
	movq	%rsi, %rdx
	setc	%cl
	subq	%r14, %rdx
	testq	%rcx, %rcx
	jne	.L1080
	testq	%rax, %rax
	jne	.L1072
	xorl	%ebx, %ebx
	xorl	%edi, %edi
.L1078:
	movl	(%r15), %eax
	subq	%r13, %r12
	leaq	4(%rdi,%rdx), %r15
	vmovq	%rdi, %xmm1
	movl	%eax, (%rdi,%rdx)
	leaq	(%r15,%r12), %rax
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqa	%xmm0, (%rsp)
	testq	%rdx, %rdx
	jg	.L1089
	testq	%r12, %r12
	jg	.L1076
	testq	%r14, %r14
	jne	.L1087
.L1077:
	vmovdqa	(%rsp), %xmm2
	movq	%rbx, 16(%rbp)
	vmovdqu	%xmm2, 0(%rbp)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1089:
	.cfi_restore_state
	movq	%r14, %rsi
	call	memmove@PLT
	testq	%r12, %r12
	jg	.L1076
.L1087:
	movq	16(%rbp), %rsi
	movq	%r14, %rdi
	subq	%r14, %rsi
	call	_ZdlPvm@PLT
	jmp	.L1077
	.p2align 4
	.p2align 3
.L1076:
	movq	%r12, %rdx
	movq	%r13, %rsi
	movq	%r15, %rdi
	call	memcpy@PLT
	testq	%r14, %r14
	je	.L1077
	jmp	.L1087
	.p2align 4
	.p2align 3
.L1080:
	movabsq	$9223372036854775804, %rbx
.L1071:
	movq	%rbx, %rdi
	movq	%rdx, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rdx
	addq	%rax, %rbx
	jmp	.L1078
	.p2align 4
	.p2align 3
.L1072:
	movabsq	$2305843009213693951, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	leaq	0(,%rax,4), %rbx
	jmp	.L1071
.L1088:
	leaq	.LC0(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7359:
	.size	_ZNSt6vectorIiSaIiEE17_M_realloc_insertIJRKiEEEvN9__gnu_cxx17__normal_iteratorIPiS1_EEDpOT_, .-_ZNSt6vectorIiSaIiEE17_M_realloc_insertIJRKiEEEvN9__gnu_cxx17__normal_iteratorIPiS1_EEDpOT_
	.section	.text._ZNSt6vectorIN11TableSearch8VariableESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,"axG",@progbits,_ZNSt6vectorIN11TableSearch8VariableESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorIN11TableSearch8VariableESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.type	_ZNSt6vectorIN11TableSearch8VariableESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, @function
_ZNSt6vectorIN11TableSearch8VariableESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_:
.LFB7390:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rdx, %rbx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %r15
	movq	(%rdi), %r13
	movabsq	$-6148914691236517205, %rdx
	movq	%r15, %rax
	subq	%r13, %rax
	sarq	$5, %rax
	imulq	%rdx, %rax
	movabsq	$96076792050570581, %rdx
	cmpq	%rdx, %rax
	je	.L1111
	testq	%rax, %rax
	movl	$1, %edx
	movq	%rdi, %rbp
	movq	%rsi, %r12
	cmovne	%rax, %rdx
	xorl	%ecx, %ecx
	addq	%rdx, %rax
	movq	%rsi, %rdx
	setc	%cl
	subq	%r13, %rdx
	testq	%rcx, %rcx
	jne	.L1103
	testq	%rax, %rax
	jne	.L1095
	xorl	%r14d, %r14d
	xorl	%edi, %edi
.L1101:
	vmovdqa	(%rbx), %xmm2
	vmovdqa	16(%rbx), %xmm3
	subq	%r12, %r15
	vmovq	%rdi, %xmm1
	vmovdqa	32(%rbx), %xmm4
	vmovdqa	48(%rbx), %xmm5
	vmovdqa	64(%rbx), %xmm6
	vmovdqa	80(%rbx), %xmm7
	leaq	96(%rdi,%rdx), %rbx
	leaq	(%rbx,%r15), %rax
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqa	%xmm0, (%rsp)
	vmovdqa	%xmm2, (%rdi,%rdx)
	vmovdqa	%xmm3, 16(%rdi,%rdx)
	vmovdqa	%xmm4, 32(%rdi,%rdx)
	vmovdqa	%xmm5, 48(%rdi,%rdx)
	vmovdqa	%xmm6, 64(%rdi,%rdx)
	vmovdqa	%xmm7, 80(%rdi,%rdx)
	testq	%rdx, %rdx
	jg	.L1112
	testq	%r15, %r15
	jg	.L1099
	testq	%r13, %r13
	jne	.L1110
.L1100:
	vmovdqa	(%rsp), %xmm0
	movq	%r14, 16(%rbp)
	vmovdqu	%xmm0, 0(%rbp)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1112:
	.cfi_restore_state
	movq	%r13, %rsi
	call	memmove@PLT
	testq	%r15, %r15
	jg	.L1099
.L1110:
	movq	16(%rbp), %rsi
	movl	$32, %edx
	movq	%r13, %rdi
	subq	%r13, %rsi
	call	_ZdlPvmSt11align_val_t@PLT
	jmp	.L1100
	.p2align 4
	.p2align 3
.L1099:
	movq	%r15, %rdx
	movq	%r12, %rsi
	movq	%rbx, %rdi
	call	memcpy@PLT
	testq	%r13, %r13
	je	.L1100
	jmp	.L1110
	.p2align 4
	.p2align 3
.L1103:
	movabsq	$9223372036854775776, %r14
.L1094:
	movq	%r14, %rdi
	movl	$32, %esi
	movq	%rdx, (%rsp)
	call	_ZnwmSt11align_val_t@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rdx
	addq	%rax, %r14
	jmp	.L1101
	.p2align 4
	.p2align 3
.L1095:
	movabsq	$96076792050570581, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	leaq	(%rax,%rax,2), %r14
	salq	$5, %r14
	jmp	.L1094
.L1111:
	leaq	.LC0(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7390:
	.size	_ZNSt6vectorIN11TableSearch8VariableESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, .-_ZNSt6vectorIN11TableSearch8VariableESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.section	.text._ZSt11__remove_ifIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops10_Iter_predIZNS2_5solveERK12TableProblemidEUlRKS3_E_EEET_SI_SI_T0_,"axG",@progbits,_ZSt11__remove_ifIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops10_Iter_predIZNS2_5solveERK12TableProblemidEUlRKS3_E_EEET_SI_SI_T0_,comdat
	.p2align 4
	.weak	_ZSt11__remove_ifIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops10_Iter_predIZNS2_5solveERK12TableProblemidEUlRKS3_E_EEET_SI_SI_T0_
	.type	_ZSt11__remove_ifIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops10_Iter_predIZNS2_5solveERK12TableProblemidEUlRKS3_E_EEET_SI_SI_T0_, @function
_ZSt11__remove_ifIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops10_Iter_predIZNS2_5solveERK12TableProblemidEUlRKS3_E_EEET_SI_SI_T0_:
.LFB7399:
	.cfi_startproc
	endbr64
	movq	%rsi, %rcx
	movq	%rdi, %rax
	subq	%rdi, %rcx
	movabsq	$-6148914691236517205, %rdi
	sarq	$5, %rcx
	imulq	%rdi, %rcx
	movq	%rcx, %rdi
	sarq	$2, %rdi
	testq	%rdi, %rdi
	jle	.L1114
	leaq	(%rdi,%rdi,2), %rcx
	vmovsd	(%rdx), %xmm0
	vmovsd	176(%rdx), %xmm1
	salq	$7, %rcx
	vsubsd	.LC8(%rip), %xmm0, %xmm0
	addq	%rax, %rcx
	jmp	.L1122
	.p2align 4
	.p2align 3
.L1147:
	vaddsd	104(%rax), %xmm1, %xmm2
	vcomisd	%xmm0, %xmm2
	jnb	.L1143
	vaddsd	200(%rax), %xmm1, %xmm2
	vcomisd	%xmm0, %xmm2
	jnb	.L1144
	vaddsd	296(%rax), %xmm1, %xmm2
	vcomisd	%xmm0, %xmm2
	jnb	.L1145
	addq	$384, %rax
	cmpq	%rcx, %rax
	je	.L1146
.L1122:
	vaddsd	8(%rax), %xmm1, %xmm2
	vcomisd	%xmm0, %xmm2
	jb	.L1147
.L1115:
	cmpq	%rsi, %rax
	je	.L1129
	leaq	96(%rax), %rdx
	cmpq	%rsi, %rdx
	je	.L1131
	.p2align 4
	.p2align 3
.L1134:
	vaddsd	8(%rdx), %xmm1, %xmm2
	vcomisd	%xmm0, %xmm2
	jnb	.L1133
	vmovdqa	(%rdx), %xmm3
	addq	$96, %rax
	vmovdqa	%xmm3, -96(%rax)
	vmovdqa	16(%rdx), %xmm4
	vmovdqa	%xmm4, -80(%rax)
	vmovdqa	32(%rdx), %xmm5
	vmovdqa	%xmm5, -64(%rax)
	vmovdqa	48(%rdx), %xmm6
	vmovdqa	%xmm6, -48(%rax)
	vmovdqa	64(%rdx), %xmm7
	vmovdqa	%xmm7, -32(%rax)
	vmovdqa	80(%rdx), %xmm3
	vmovdqa	%xmm3, -16(%rax)
.L1133:
	addq	$96, %rdx
	cmpq	%rdx, %rsi
	jne	.L1134
.L1131:
	ret
	.p2align 4
	.p2align 3
.L1146:
	movq	%rsi, %rcx
	movabsq	$-6148914691236517205, %rdi
	subq	%rax, %rcx
	sarq	$5, %rcx
	imulq	%rdi, %rcx
.L1114:
	cmpq	$2, %rcx
	je	.L1123
	cmpq	$3, %rcx
	je	.L1124
	cmpq	$1, %rcx
	je	.L1148
.L1129:
	movq	%rsi, %rax
	ret
.L1148:
	vmovsd	(%rdx), %xmm0
	vmovsd	176(%rdx), %xmm1
	vsubsd	.LC8(%rip), %xmm0, %xmm0
.L1128:
	vaddsd	8(%rax), %xmm1, %xmm2
	vcomisd	%xmm0, %xmm2
	jb	.L1129
	jmp	.L1115
.L1124:
	vmovsd	176(%rdx), %xmm1
	vmovsd	(%rdx), %xmm0
	vsubsd	.LC8(%rip), %xmm0, %xmm0
	vaddsd	8(%rax), %xmm1, %xmm2
	vcomisd	%xmm0, %xmm2
	jnb	.L1115
	addq	$96, %rax
	jmp	.L1127
.L1123:
	vmovsd	(%rdx), %xmm0
	vmovsd	176(%rdx), %xmm1
	vsubsd	.LC8(%rip), %xmm0, %xmm0
.L1127:
	vaddsd	8(%rax), %xmm1, %xmm2
	vcomisd	%xmm0, %xmm2
	jnb	.L1115
	addq	$96, %rax
	jmp	.L1128
	.p2align 4
	.p2align 3
.L1143:
	addq	$96, %rax
	jmp	.L1115
	.p2align 4
	.p2align 3
.L1144:
	addq	$192, %rax
	jmp	.L1115
	.p2align 4
	.p2align 3
.L1145:
	addq	$288, %rax
	jmp	.L1115
	.cfi_endproc
.LFE7399:
	.size	_ZSt11__remove_ifIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops10_Iter_predIZNS2_5solveERK12TableProblemidEUlRKS3_E_EEET_SI_SI_T0_, .-_ZSt11__remove_ifIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops10_Iter_predIZNS2_5solveERK12TableProblemidEUlRKS3_E_EEET_SI_SI_T0_
	.section	.text._ZNSt6vectorI6ValuesSaIS0_EE14_M_fill_assignEmRKS0_,"axG",@progbits,_ZNSt6vectorI6ValuesSaIS0_EE14_M_fill_assignEmRKS0_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI6ValuesSaIS0_EE14_M_fill_assignEmRKS0_
	.type	_ZNSt6vectorI6ValuesSaIS0_EE14_M_fill_assignEmRKS0_, @function
_ZNSt6vectorI6ValuesSaIS0_EE14_M_fill_assignEmRKS0_:
.LFB7406:
	.cfi_startproc
	endbr64
	pushq	%r12
	.cfi_def_cfa_offset 16
	.cfi_offset 12, -16
	pushq	%rbp
	.cfi_def_cfa_offset 24
	.cfi_offset 6, -24
	movq	%rdi, %rbp
	pushq	%rbx
	.cfi_def_cfa_offset 32
	.cfi_offset 3, -32
	movq	16(%rbp), %r8
	movq	(%rdi), %rdi
	movq	%rdx, %rbx
	subq	%rdi, %r8
	movq	%r8, %rax
	sarq	$6, %rax
	cmpq	%rsi, %rax
	jb	.L1178
	movq	8(%rbp), %rax
	movq	%rax, %rdx
	subq	%rdi, %rdx
	sarq	$6, %rdx
	cmpq	%rdx, %rsi
	jbe	.L1157
	cmpq	%rax, %rdi
	je	.L1161
	.p2align 4
	.p2align 3
.L1158:
	vmovdqa	(%rbx), %xmm5
	addq	$64, %rdi
	vmovdqa	%xmm5, -64(%rdi)
	vmovdqa	16(%rbx), %xmm6
	vmovdqa	%xmm6, -48(%rdi)
	vmovdqa	32(%rbx), %xmm7
	vmovdqa	%xmm7, -32(%rdi)
	vmovdqa	48(%rbx), %xmm4
	vmovdqa	%xmm4, -16(%rdi)
	cmpq	%rdi, %rax
	jne	.L1158
.L1161:
	subq	%rdx, %rsi
	salq	$6, %rsi
	addq	%rax, %rsi
	cmpq	%rsi, %rax
	je	.L1160
	.p2align 4
	.p2align 3
.L1159:
	vmovdqa	(%rbx), %xmm1
	addq	$64, %rax
	vmovdqa	%xmm1, -64(%rax)
	vmovdqa	16(%rbx), %xmm2
	vmovdqa	%xmm2, -48(%rax)
	vmovdqa	32(%rbx), %xmm3
	vmovdqa	%xmm3, -32(%rax)
	vmovdqa	48(%rbx), %xmm0
	vmovdqa	%xmm0, -16(%rax)
	cmpq	%rax, %rsi
	jne	.L1159
.L1160:
	movq	%rsi, 8(%rbp)
.L1176:
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1157:
	.cfi_restore_state
	movq	%rdi, %rdx
	testq	%rsi, %rsi
	je	.L1162
	salq	$6, %rsi
	leaq	(%rdi,%rsi), %rdx
	cmpq	%rdx, %rdi
	je	.L1162
	.p2align 4
	.p2align 3
.L1163:
	vmovdqa	(%rbx), %xmm1
	addq	$64, %rdi
	vmovdqa	%xmm1, -64(%rdi)
	vmovdqa	16(%rbx), %xmm2
	vmovdqa	%xmm2, -48(%rdi)
	vmovdqa	32(%rbx), %xmm3
	vmovdqa	%xmm3, -32(%rdi)
	vmovdqa	48(%rbx), %xmm5
	vmovdqa	%xmm5, -16(%rdi)
	cmpq	%rdi, %rdx
	jne	.L1163
.L1162:
	cmpq	%rdx, %rax
	je	.L1176
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	movq	%rdx, 8(%rbp)
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1178:
	.cfi_restore_state
	movq	%rsi, %rax
	shrq	$57, %rax
	jne	.L1179
	movq	%rsi, %r12
	salq	$6, %r12
	testq	%rsi, %rsi
	je	.L1164
	movl	$32, %esi
	movq	%r12, %rdi
	call	_ZnwmSt11align_val_t@PLT
	leaq	(%rax,%r12), %rcx
	cmpq	%rcx, %rax
	je	.L1153
	vmovdqa	(%rbx), %xmm3
	vmovdqa	16(%rbx), %xmm2
	movq	%rax, %rdx
	vmovdqa	32(%rbx), %xmm1
	vmovdqa	48(%rbx), %xmm0
	.p2align 4
	.p2align 3
.L1154:
	vmovdqa	%xmm3, (%rdx)
	vmovdqa	%xmm2, 16(%rdx)
	addq	$64, %rdx
	vmovdqa	%xmm1, -32(%rdx)
	vmovdqa	%xmm0, -16(%rdx)
	cmpq	%rcx, %rdx
	jne	.L1154
.L1153:
	movq	0(%rbp), %rdi
	movq	16(%rbp), %r8
	subq	%rdi, %r8
.L1152:
	vmovq	%rax, %xmm4
	movq	%rcx, 16(%rbp)
	vpinsrq	$1, %rcx, %xmm4, %xmm0
	vmovdqu	%xmm0, 0(%rbp)
	testq	%rdi, %rdi
	je	.L1176
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	movl	$32, %edx
	movq	%r8, %rsi
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	jmp	_ZdlPvmSt11align_val_t@PLT
	.p2align 4
	.p2align 3
.L1164:
	.cfi_restore_state
	xorl	%eax, %eax
	xorl	%ecx, %ecx
	jmp	.L1152
.L1179:
	leaq	.LC11(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7406:
	.size	_ZNSt6vectorI6ValuesSaIS0_EE14_M_fill_assignEmRKS0_, .-_ZNSt6vectorI6ValuesSaIS0_EE14_M_fill_assignEmRKS0_
	.section	.text._ZNSt6vectorIiSaIiEE17_M_default_appendEm,"axG",@progbits,_ZNSt6vectorIiSaIiEE17_M_default_appendEm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorIiSaIiEE17_M_default_appendEm
	.type	_ZNSt6vectorIiSaIiEE17_M_default_appendEm, @function
_ZNSt6vectorIiSaIiEE17_M_default_appendEm:
.LFB7426:
	.cfi_startproc
	endbr64
	testq	%rsi, %rsi
	je	.L1210
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movabsq	$2305843009213693951, %rcx
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rdi, %r12
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %rdx
	movq	(%rdi), %r14
	movq	%rsi, %rbx
	movq	16(%rdi), %rax
	movq	%rdx, %rbp
	subq	%r14, %rbp
	subq	%rdx, %rax
	movq	%rbp, %r13
	sarq	$2, %rax
	sarq	$2, %r13
	subq	%r13, %rcx
	cmpq	%rax, %rsi
	jbe	.L1213
	cmpq	%rsi, %rcx
	jb	.L1214
	cmpq	%r13, %rsi
	movq	%r13, %rax
	cmovnb	%rsi, %rax
	addq	%r13, %rax
	jc	.L1186
	testq	%rax, %rax
	jne	.L1215
	movq	%rbp, %r8
	xorl	%r15d, %r15d
	xorl	%ecx, %ecx
.L1188:
	movq	%rbx, %rdx
	addq	%rcx, %rbp
	decq	%rdx
	movl	$0, 0(%rbp)
	je	.L1192
	leaq	4(%rbp), %rdi
	salq	$2, %rdx
	xorl	%esi, %esi
	movq	%r8, 8(%rsp)
	movq	%rcx, (%rsp)
	call	memset@PLT
	movq	(%rsp), %rcx
	movq	8(%rsp), %r8
.L1192:
	testq	%r8, %r8
	jg	.L1216
	testq	%r14, %r14
	jne	.L1217
.L1194:
	addq	%r13, %rbx
	vmovq	%rcx, %xmm1
	movq	%r15, 16(%r12)
	leaq	(%rcx,%rbx,4), %rax
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqu	%xmm0, (%r12)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1213:
	.cfi_restore_state
	decq	%rbx
	movl	$0, (%rdx)
	leaq	4(%rdx), %rcx
	je	.L1183
	leaq	(%rcx,%rbx,4), %rax
	movq	%rcx, %rdi
	xorl	%esi, %esi
	subq	%rdx, %rax
	leaq	-4(%rax), %rbx
	movq	%rbx, %rdx
	call	memset@PLT
	movq	%rax, %rcx
	addq	%rbx, %rcx
.L1183:
	movq	%rcx, 8(%r12)
	addq	$24, %rsp
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1210:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L1216:
	.cfi_def_cfa_offset 80
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	movq	%r14, %rsi
	movq	%rcx, %rdi
	movq	%r8, %rdx
	call	memmove@PLT
	movq	16(%r12), %rsi
	movq	%rax, %rcx
	subq	%r14, %rsi
.L1193:
	movq	%r14, %rdi
	movq	%rcx, (%rsp)
	call	_ZdlPvm@PLT
	movq	(%rsp), %rcx
	jmp	.L1194
	.p2align 4
	.p2align 3
.L1217:
	movq	16(%r12), %rsi
	subq	%r14, %rsi
	jmp	.L1193
.L1215:
	movabsq	$2305843009213693951, %r15
	cmpq	%r15, %rax
	cmovbe	%rax, %r15
	salq	$2, %r15
.L1187:
	movq	%r15, %rdi
	call	_Znwm@PLT
	movq	(%r12), %r14
	movq	8(%r12), %r8
	movq	%rax, %rcx
	addq	%rax, %r15
	subq	%r14, %r8
	jmp	.L1188
.L1186:
	movabsq	$9223372036854775804, %r15
	jmp	.L1187
.L1214:
	leaq	.LC10(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7426:
	.size	_ZNSt6vectorIiSaIiEE17_M_default_appendEm, .-_ZNSt6vectorIiSaIiEE17_M_default_appendEm
	.section	.text._ZSt13__heap_selectIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_SA_T0_,"axG",@progbits,_ZSt13__heap_selectIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_SA_T0_,comdat
	.p2align 4
	.weak	_ZSt13__heap_selectIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_SA_T0_
	.type	_ZSt13__heap_selectIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_SA_T0_, @function
_ZSt13__heap_selectIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_SA_T0_:
.LFB7621:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	movq	%rsi, %rax
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	movq	%rdi, %r12
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	subq	%r12, %rax
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	%rsi, %rdi
	movq	%rdx, %rbx
	movq	%rax, %r15
	sarq	$4, %r15
	cmpq	$16, %rax
	jle	.L1219
	leaq	-2(%r15), %rax
	movq	%r15, %r11
	movq	%rax, %r10
	notq	%r11
	shrq	$63, %r10
	andl	$1, %r11d
	addq	%rax, %r10
	leaq	-1(%r15), %rax
	sarq	%r10
	movq	%rax, %r8
	shrq	$63, %r8
	movq	%r10, %r9
	movq	%r10, %rsi
	addq	%rax, %r8
	salq	$4, %r9
	sarq	%r8
	addq	%r12, %r9
	.p2align 4
	.p2align 3
.L1232:
	vmovsd	(%r9), %xmm2
	movq	8(%r9), %r14
	movq	%r9, %rax
	cmpq	%r8, %rsi
	jge	.L1220
	movq	%rsi, %rbp
	movq	%rsi, 8(%rsp)
	jmp	.L1225
	.p2align 4
	.p2align 3
.L1221:
	movq	8(%rax), %rsi
	cmpq	%rsi, 8(%rcx)
	jbe	.L1223
	movq	%rcx, %rax
	movq	%r13, %rdx
.L1223:
	vmovdqu	(%rax), %xmm4
	salq	$4, %rbp
	vmovdqu	%xmm4, (%r12,%rbp)
	cmpq	%rdx, %r8
	jle	.L1268
	movq	%rdx, %rbp
.L1225:
	leaq	1(%rbp), %rax
	leaq	(%rax,%rax), %rdx
	salq	$5, %rax
	leaq	-1(%rdx), %r13
	addq	%r12, %rax
	movq	%r13, %rcx
	vmovsd	(%rax), %xmm0
	salq	$4, %rcx
	addq	%r12, %rcx
	vmovsd	(%rcx), %xmm1
	vucomisd	%xmm0, %xmm1
	jp	.L1246
	je	.L1221
.L1246:
	vucomisd	%xmm0, %xmm1
	cmova	%rcx, %rax
	cmova	%r13, %rdx
	jmp	.L1223
	.p2align 4
	.p2align 3
.L1268:
	movq	8(%rsp), %rsi
	cmpq	%rdx, %r10
	jne	.L1226
	testb	%r11b, %r11b
	jne	.L1241
.L1226:
	leaq	-1(%rdx), %rcx
	movq	%rcx, %rbp
	shrq	$63, %rbp
	addq	%rcx, %rbp
	sarq	%rbp
	cmpq	%rdx, %rsi
	jl	.L1231
	jmp	.L1227
	.p2align 4
	.p2align 3
.L1228:
	cmpq	%r14, 8(%rcx)
	setb	%r13b
.L1230:
	salq	$4, %rdx
	addq	%r12, %rdx
	testb	%r13b, %r13b
	je	.L1269
	vmovdqu	(%rcx), %xmm3
	vmovdqu	%xmm3, (%rdx)
	leaq	-1(%rbp), %rdx
	movq	%rdx, %rax
	shrq	$63, %rax
	addq	%rdx, %rax
	movq	%rbp, %rdx
	sarq	%rax
	cmpq	%rbp, %rsi
	jge	.L1270
	movq	%rax, %rbp
.L1231:
	movq	%rbp, %rcx
	salq	$4, %rcx
	addq	%r12, %rcx
	vmovsd	(%rcx), %xmm0
	vucomisd	%xmm2, %xmm0
	jp	.L1248
	je	.L1228
.L1248:
	vcomisd	%xmm0, %xmm2
	seta	%r13b
	jmp	.L1230
.L1269:
	movq	%rdx, %rax
.L1227:
	vmovsd	%xmm2, (%rax)
	movq	%r14, 8(%rax)
	subq	$16, %r9
	testq	%rsi, %rsi
	je	.L1219
	decq	%rsi
	jmp	.L1232
	.p2align 4
	.p2align 3
.L1270:
	movq	%rcx, %rax
	jmp	.L1227
	.p2align 4
	.p2align 3
.L1219:
	movq	%rdi, %rbp
	cmpq	%rdi, %rbx
	ja	.L1238
	jmp	.L1266
	.p2align 4
	.p2align 3
.L1234:
	movq	8(%r12), %rax
	cmpq	%rax, 8(%rbp)
	jb	.L1236
.L1237:
	addq	$16, %rbp
	cmpq	%rbp, %rbx
	jbe	.L1266
.L1238:
	vmovsd	0(%rbp), %xmm0
	vmovsd	(%r12), %xmm1
	vucomisd	%xmm1, %xmm0
	jp	.L1249
	je	.L1234
.L1249:
	vcomisd	%xmm0, %xmm1
	jbe	.L1237
.L1236:
	vmovdqu	(%r12), %xmm5
	movq	0(%rbp), %rax
	movq	%r15, %rsi
	movq	%r12, %rdi
	movq	8(%rbp), %rdx
	addq	$16, %rbp
	vmovq	%rax, %xmm0
	vmovdqu	%xmm5, -16(%rbp)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_less_iterEEvT_T0_SB_T1_T2_.constprop.0
	cmpq	%rbp, %rbx
	ja	.L1238
.L1266:
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1220:
	.cfi_restore_state
	cmpq	%rsi, %r10
	jne	.L1227
	movq	%rsi, %rdx
	testb	%r11b, %r11b
	je	.L1227
.L1241:
	leaq	1(%rdx,%rdx), %rdx
	movq	%rdx, %rcx
	salq	$4, %rcx
	addq	%r12, %rcx
	vmovdqu	(%rcx), %xmm6
	vmovdqu	%xmm6, (%rax)
	movq	%rcx, %rax
	jmp	.L1226
	.cfi_endproc
.LFE7621:
	.size	_ZSt13__heap_selectIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_SA_T0_, .-_ZSt13__heap_selectIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_SA_T0_
	.text
	.p2align 4
	.type	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElNS0_5__ops15_Iter_less_iterEEvT_SA_T0_T1_.isra.0, @function
_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElNS0_5__ops15_Iter_less_iterEEvT_SA_T0_T1_.isra.0:
.LFB8890:
	.cfi_startproc
	movq	%rsi, %rax
	subq	%rdi, %rax
	cmpq	$256, %rax
	jle	.L1334
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	movq	%rsi, %r12
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	%rdx, %r13
	movq	%rdi, %rbx
	leaq	16(%rdi), %rbp
	subq	$8, %rsp
	.cfi_def_cfa_offset 48
	testq	%rdx, %rdx
	je	.L1274
.L1275:
	movq	%rsi, %rax
	vmovsd	16(%rbx), %xmm1
	decq	%r13
	subq	%rbx, %rax
	movq	%rax, %rcx
	shrq	$63, %rax
	sarq	$4, %rcx
	addq	%rax, %rcx
	sarq	%rcx
	salq	$4, %rcx
	addq	%rbx, %rcx
	vmovsd	(%rcx), %xmm2
	vucomisd	%xmm2, %xmm1
	jp	.L1316
	jne	.L1316
	movq	8(%rcx), %rax
	cmpq	%rax, 24(%rbx)
	setb	%al
.L1280:
	vmovsd	-16(%rsi), %xmm0
	testb	%al, %al
	je	.L1335
	vucomisd	%xmm0, %xmm2
	jp	.L1317
	jne	.L1317
	movq	-8(%rsi), %rax
	cmpq	%rax, 8(%rcx)
	jnb	.L1284
.L1283:
	vmovsd	(%rbx), %xmm0
	vmovdqu	(%rcx), %xmm5
	movq	8(%rbx), %rax
	vmovdqu	%xmm5, (%rbx)
	vmovsd	%xmm0, (%rcx)
	movq	%rax, 8(%rcx)
.L1285:
	movq	%rsi, %rdx
	movq	%rbp, %rax
	.p2align 4
	.p2align 3
.L1307:
	vmovsd	(%rbx), %xmm0
	.p2align 4
	.p2align 3
.L1310:
	vmovsd	(%rax), %xmm1
	movq	%rax, %r12
	vucomisd	%xmm0, %xmm1
	jp	.L1321
	jne	.L1321
	movq	8(%rbx), %rdi
	addq	$16, %rax
	cmpq	%rdi, 8(%r12)
	jb	.L1310
.L1300:
	leaq	-16(%rdx), %rax
	.p2align 4
	.p2align 3
.L1309:
	vmovsd	(%rax), %xmm2
	movq	%rax, %rdx
	vucomisd	%xmm2, %xmm0
	jp	.L1322
	jne	.L1322
	movq	8(%rdx), %rcx
	subq	$16, %rax
	cmpq	%rcx, 8(%rbx)
	jb	.L1309
	cmpq	%rdx, %r12
	jnb	.L1336
.L1305:
	vmovdqu	(%rdx), %xmm3
	movq	8(%r12), %rax
	vmovdqu	%xmm3, (%r12)
	movq	%rax, 8(%rdx)
	vmovsd	%xmm1, (%rdx)
	leaq	16(%r12), %rax
	jmp	.L1307
	.p2align 4
	.p2align 3
.L1322:
	subq	$16, %rax
	vcomisd	%xmm0, %xmm2
	ja	.L1309
	cmpq	%rdx, %r12
	jb	.L1305
.L1336:
	movq	%r13, %rdx
	movq	%r12, %rdi
	call	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElNS0_5__ops15_Iter_less_iterEEvT_SA_T0_T1_.isra.0
	movq	%r12, %rax
	subq	%rbx, %rax
	cmpq	$256, %rax
	jle	.L1330
	testq	%r13, %r13
	je	.L1274
	movq	%r12, %rsi
	jmp	.L1275
	.p2align 4
	.p2align 3
.L1321:
	addq	$16, %rax
	vcomisd	%xmm1, %xmm0
	ja	.L1310
	jmp	.L1300
.L1335:
	vucomisd	%xmm0, %xmm1
	jp	.L1319
	jne	.L1319
	movq	-8(%rsi), %rax
	cmpq	%rax, 24(%rbx)
	setb	%al
.L1292:
	vmovsd	(%rbx), %xmm1
	movq	8(%rbx), %rdx
	testb	%al, %al
	je	.L1337
	vmovdqu	16(%rbx), %xmm6
	vmovsd	%xmm1, 16(%rbx)
	movq	%rdx, 24(%rbx)
	vmovdqu	%xmm6, (%rbx)
	jmp	.L1285
.L1316:
	vcomisd	%xmm1, %xmm2
	seta	%al
	jmp	.L1280
.L1317:
	vcomisd	%xmm2, %xmm0
	ja	.L1283
.L1284:
	vucomisd	%xmm0, %xmm1
	jp	.L1318
	jne	.L1318
	movq	-8(%rsi), %rax
	cmpq	%rax, 24(%rbx)
	jnb	.L1289
.L1288:
	vmovsd	(%rbx), %xmm0
	vmovdqu	-16(%rsi), %xmm7
	movq	8(%rbx), %rax
	vmovdqu	%xmm7, (%rbx)
	vmovsd	%xmm0, -16(%rsi)
	movq	%rax, -8(%rsi)
	jmp	.L1285
.L1337:
	vucomisd	%xmm0, %xmm2
	jp	.L1320
	jne	.L1320
	movq	-8(%rsi), %rax
	cmpq	%rax, 8(%rcx)
	jnb	.L1296
.L1295:
	vmovdqu	-16(%rsi), %xmm7
	vmovdqu	%xmm7, (%rbx)
	vmovsd	%xmm1, -16(%rsi)
	movq	%rdx, -8(%rsi)
	jmp	.L1285
.L1274:
	movq	%r12, %rdx
	movq	%r12, %rsi
	movq	%rbx, %rdi
	call	_ZSt13__heap_selectIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_SA_T0_
	.p2align 4
	.p2align 3
.L1276:
	vmovdqu	(%rbx), %xmm4
	subq	$16, %r12
	movq	(%r12), %rax
	movq	%rbx, %rdi
	movq	%r12, %rbp
	movq	8(%r12), %rdx
	subq	%rbx, %rbp
	movq	%rbp, %rsi
	sarq	$4, %rsi
	vmovq	%rax, %xmm0
	vmovdqu	%xmm4, (%r12)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_less_iterEEvT_T0_SB_T1_T2_.constprop.0
	cmpq	$16, %rbp
	jg	.L1276
.L1330:
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
.L1319:
	.cfi_restore_state
	vcomisd	%xmm1, %xmm0
	seta	%al
	jmp	.L1292
.L1320:
	vcomisd	%xmm2, %xmm0
	ja	.L1295
.L1296:
	vmovdqu	(%rcx), %xmm5
	vmovdqu	%xmm5, (%rbx)
	vmovsd	%xmm1, (%rcx)
	movq	%rdx, 8(%rcx)
	jmp	.L1285
.L1318:
	vcomisd	%xmm1, %xmm0
	ja	.L1288
.L1289:
	vmovdqu	16(%rbx), %xmm7
	vmovsd	(%rbx), %xmm0
	movq	8(%rbx), %rax
	movq	%rax, 24(%rbx)
	vmovdqu	%xmm7, (%rbx)
	vmovsd	%xmm0, 16(%rbx)
	jmp	.L1285
.L1334:
	.cfi_def_cfa_offset 8
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	ret
	.cfi_endproc
.LFE8890:
	.size	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElNS0_5__ops15_Iter_less_iterEEvT_SA_T0_T1_.isra.0, .-_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElNS0_5__ops15_Iter_less_iterEEvT_SA_T0_T1_.isra.0
	.section	.text._ZSt6__sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.constprop.0,"axG",@progbits,_ZN9Optimizer3runEv,comdat
	.p2align 4
	.type	_ZSt6__sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.constprop.0, @function
_ZSt6__sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.constprop.0:
.LFB8895:
	.cfi_startproc
	cmpq	%rsi, %rdi
	je	.L1353
	pushq	%r12
	.cfi_def_cfa_offset 16
	.cfi_offset 12, -16
	pushq	%rbp
	.cfi_def_cfa_offset 24
	.cfi_offset 6, -24
	pushq	%rbx
	.cfi_def_cfa_offset 32
	.cfi_offset 3, -32
	movq	%rsi, %rbx
	subq	%rdi, %rbx
	movl	$63, %edx
	movq	%rdi, %r12
	movq	%rsi, %rbp
	movq	%rbx, %rax
	sarq	$4, %rax
	lzcntq	%rax, %rax
	subl	%eax, %edx
	movslq	%edx, %rdx
	addq	%rdx, %rdx
	call	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElNS0_5__ops15_Iter_less_iterEEvT_SA_T0_T1_.isra.0
	cmpq	$256, %rbx
	jle	.L1340
	leaq	256(%r12), %rbx
	movq	%r12, %rdi
	movq	%rbx, %rsi
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0
	cmpq	%rbx, %rbp
	je	.L1351
	movq	%rbx, %rcx
	.p2align 4
	.p2align 3
.L1347:
	vmovsd	(%rcx), %xmm1
	movq	8(%rcx), %rdx
	movq	%rcx, %rax
	jmp	.L1342
	.p2align 4
	.p2align 3
.L1343:
	cmpq	-8(%rax), %rdx
	jnb	.L1346
.L1345:
	vmovdqu	-16(%rax), %xmm2
	subq	$16, %rax
	vmovdqu	%xmm2, 16(%rax)
.L1342:
	vmovsd	-16(%rax), %xmm0
	vucomisd	%xmm0, %xmm1
	jp	.L1349
	je	.L1343
.L1349:
	vcomisd	%xmm1, %xmm0
	ja	.L1345
.L1346:
	addq	$16, %rcx
	vmovsd	%xmm1, (%rax)
	movq	%rdx, 8(%rax)
	cmpq	%rcx, %rbp
	jne	.L1347
.L1351:
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1340:
	.cfi_restore_state
	popq	%rbx
	.cfi_restore 3
	.cfi_def_cfa_offset 24
	movq	%rbp, %rsi
	movq	%r12, %rdi
	popq	%rbp
	.cfi_restore 6
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_restore 12
	.cfi_def_cfa_offset 8
	jmp	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0
	.p2align 4
	.p2align 3
.L1353:
	ret
	.cfi_endproc
.LFE8895:
	.size	_ZSt6__sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.constprop.0, .-_ZSt6__sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.constprop.0
	.section	.text._ZNSt6vectorISt4pairIdiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,"axG",@progbits,_ZNSt6vectorISt4pairIdiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorISt4pairIdiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.type	_ZNSt6vectorISt4pairIdiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, @function
_ZNSt6vectorISt4pairIdiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_:
.LFB7715:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movabsq	$576460752303423487, %rcx
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	subq	$40, %rsp
	.cfi_def_cfa_offset 96
	movq	8(%rdi), %r14
	movq	(%rdi), %r12
	movq	%r14, %rax
	subq	%r12, %rax
	sarq	$4, %rax
	cmpq	%rcx, %rax
	je	.L1375
	testq	%rax, %rax
	movl	$1, %ecx
	movq	%rsi, %rbp
	movq	%rdi, %r13
	cmovne	%rax, %rcx
	addq	%rcx, %rax
	setc	%cl
	subq	%r12, %rsi
	movzbl	%cl, %ecx
	testq	%rcx, %rcx
	jne	.L1367
	testq	%rax, %rax
	jne	.L1361
	movl	$16, %ecx
	xorl	%ebx, %ebx
	xorl	%r15d, %r15d
.L1366:
	vmovdqu	(%rdx), %xmm3
	vmovdqu	%xmm3, (%r15,%rsi)
	cmpq	%r12, %rbp
	je	.L1362
	movq	%rbp, %rcx
	movq	%r15, %rdx
	movq	%r12, %rax
	subq	%r12, %rcx
	.p2align 4
	.p2align 3
.L1363:
	vmovdqu	(%rax), %xmm2
	addq	$16, %rax
	addq	$16, %rdx
	vmovdqu	%xmm2, -16(%rdx)
	cmpq	%rbp, %rax
	jne	.L1363
	leaq	16(%r15,%rcx), %rcx
.L1362:
	cmpq	%r14, %rbp
	je	.L1364
	subq	%rbp, %r14
	movq	%rcx, %rdi
	movq	%rbp, %rsi
	movq	%r14, %rdx
	call	memcpy@PLT
	movq	%rax, %rcx
	addq	%r14, %rcx
.L1364:
	vmovq	%r15, %xmm1
	vpinsrq	$1, %rcx, %xmm1, %xmm0
	testq	%r12, %r12
	je	.L1365
	movq	16(%r13), %rsi
	movq	%r12, %rdi
	vmovdqa	%xmm0, (%rsp)
	subq	%r12, %rsi
	call	_ZdlPvm@PLT
	vmovdqa	(%rsp), %xmm0
.L1365:
	vmovdqu	%xmm0, 0(%r13)
	movq	%rbx, 16(%r13)
	addq	$40, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1367:
	.cfi_restore_state
	movabsq	$9223372036854775792, %rbx
.L1360:
	movq	%rbx, %rdi
	movq	%rdx, 24(%rsp)
	movq	%rsi, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %r15
	movq	(%rsp), %rsi
	movq	24(%rsp), %rdx
	addq	%rax, %rbx
	leaq	16(%rax), %rcx
	jmp	.L1366
.L1361:
	movabsq	$576460752303423487, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	salq	$4, %rax
	movq	%rax, %rbx
	jmp	.L1360
.L1375:
	leaq	.LC0(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7715:
	.size	_ZNSt6vectorISt4pairIdiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, .-_ZNSt6vectorISt4pairIdiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.section	.text._ZNSt6vectorIjSaIjEE17_M_realloc_insertIJjEEEvN9__gnu_cxx17__normal_iteratorIPjS1_EEDpOT_,"axG",@progbits,_ZNSt6vectorIjSaIjEE17_M_realloc_insertIJjEEEvN9__gnu_cxx17__normal_iteratorIPjS1_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorIjSaIjEE17_M_realloc_insertIJjEEEvN9__gnu_cxx17__normal_iteratorIPjS1_EEDpOT_
	.type	_ZNSt6vectorIjSaIjEE17_M_realloc_insertIJjEEEvN9__gnu_cxx17__normal_iteratorIPjS1_EEDpOT_, @function
_ZNSt6vectorIjSaIjEE17_M_realloc_insertIJjEEEvN9__gnu_cxx17__normal_iteratorIPjS1_EEDpOT_:
.LFB7743:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movq	%rdx, %r15
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movabsq	$2305843009213693951, %rdx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %r12
	movq	(%rdi), %r14
	movq	%r12, %rax
	subq	%r14, %rax
	sarq	$2, %rax
	cmpq	%rdx, %rax
	je	.L1397
	testq	%rax, %rax
	movl	$1, %edx
	movq	%rdi, %rbp
	movq	%rsi, %r13
	cmovne	%rax, %rdx
	xorl	%ecx, %ecx
	addq	%rdx, %rax
	movq	%rsi, %rdx
	setc	%cl
	subq	%r14, %rdx
	testq	%rcx, %rcx
	jne	.L1389
	testq	%rax, %rax
	jne	.L1381
	xorl	%ebx, %ebx
	xorl	%edi, %edi
.L1387:
	movl	(%r15), %eax
	subq	%r13, %r12
	leaq	4(%rdi,%rdx), %r15
	vmovq	%rdi, %xmm1
	movl	%eax, (%rdi,%rdx)
	leaq	(%r15,%r12), %rax
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqa	%xmm0, (%rsp)
	testq	%rdx, %rdx
	jg	.L1398
	testq	%r12, %r12
	jg	.L1385
	testq	%r14, %r14
	jne	.L1396
.L1386:
	vmovdqa	(%rsp), %xmm2
	movq	%rbx, 16(%rbp)
	vmovdqu	%xmm2, 0(%rbp)
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1398:
	.cfi_restore_state
	movq	%r14, %rsi
	call	memmove@PLT
	testq	%r12, %r12
	jg	.L1385
.L1396:
	movq	16(%rbp), %rsi
	movq	%r14, %rdi
	subq	%r14, %rsi
	call	_ZdlPvm@PLT
	jmp	.L1386
	.p2align 4
	.p2align 3
.L1385:
	movq	%r12, %rdx
	movq	%r13, %rsi
	movq	%r15, %rdi
	call	memcpy@PLT
	testq	%r14, %r14
	je	.L1386
	jmp	.L1396
	.p2align 4
	.p2align 3
.L1389:
	movabsq	$9223372036854775804, %rbx
.L1380:
	movq	%rbx, %rdi
	movq	%rdx, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rdx
	addq	%rax, %rbx
	jmp	.L1387
	.p2align 4
	.p2align 3
.L1381:
	movabsq	$2305843009213693951, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	leaq	0(,%rax,4), %rbx
	jmp	.L1380
.L1397:
	leaq	.LC0(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7743:
	.size	_ZNSt6vectorIjSaIjEE17_M_realloc_insertIJjEEEvN9__gnu_cxx17__normal_iteratorIPjS1_EEDpOT_, .-_ZNSt6vectorIjSaIjEE17_M_realloc_insertIJjEEEvN9__gnu_cxx17__normal_iteratorIPjS1_EEDpOT_
	.section	.text._ZNSt6vectorISt4pairIjmESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,"axG",@progbits,_ZNSt6vectorISt4pairIjmESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorISt4pairIjmESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.type	_ZNSt6vectorISt4pairIjmESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, @function
_ZNSt6vectorISt4pairIjmESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_:
.LFB7754:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movabsq	$576460752303423487, %rcx
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	subq	$40, %rsp
	.cfi_def_cfa_offset 96
	movq	8(%rdi), %r14
	movq	(%rdi), %r12
	movq	%r14, %rax
	subq	%r12, %rax
	sarq	$4, %rax
	cmpq	%rcx, %rax
	je	.L1418
	testq	%rax, %rax
	movl	$1, %ecx
	movq	%rsi, %rbp
	movq	%rdi, %r13
	cmovne	%rax, %rcx
	addq	%rcx, %rax
	setc	%cl
	subq	%r12, %rsi
	movzbl	%cl, %ecx
	testq	%rcx, %rcx
	jne	.L1410
	testq	%rax, %rax
	jne	.L1404
	movl	$16, %ecx
	xorl	%ebx, %ebx
	xorl	%r15d, %r15d
.L1409:
	vmovdqu	(%rdx), %xmm3
	vmovdqu	%xmm3, (%r15,%rsi)
	cmpq	%r12, %rbp
	je	.L1405
	movq	%rbp, %rcx
	movq	%r15, %rdx
	movq	%r12, %rax
	subq	%r12, %rcx
	.p2align 4
	.p2align 3
.L1406:
	vmovdqu	(%rax), %xmm2
	addq	$16, %rax
	addq	$16, %rdx
	vmovdqu	%xmm2, -16(%rdx)
	cmpq	%rbp, %rax
	jne	.L1406
	leaq	16(%r15,%rcx), %rcx
.L1405:
	cmpq	%r14, %rbp
	je	.L1407
	subq	%rbp, %r14
	movq	%rcx, %rdi
	movq	%rbp, %rsi
	movq	%r14, %rdx
	call	memcpy@PLT
	movq	%rax, %rcx
	addq	%r14, %rcx
.L1407:
	vmovq	%r15, %xmm1
	vpinsrq	$1, %rcx, %xmm1, %xmm0
	testq	%r12, %r12
	je	.L1408
	movq	16(%r13), %rsi
	movq	%r12, %rdi
	vmovdqa	%xmm0, (%rsp)
	subq	%r12, %rsi
	call	_ZdlPvm@PLT
	vmovdqa	(%rsp), %xmm0
.L1408:
	vmovdqu	%xmm0, 0(%r13)
	movq	%rbx, 16(%r13)
	addq	$40, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1410:
	.cfi_restore_state
	movabsq	$9223372036854775792, %rbx
.L1403:
	movq	%rbx, %rdi
	movq	%rdx, 24(%rsp)
	movq	%rsi, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %r15
	movq	(%rsp), %rsi
	movq	24(%rsp), %rdx
	addq	%rax, %rbx
	leaq	16(%rax), %rcx
	jmp	.L1409
.L1404:
	movabsq	$576460752303423487, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	salq	$4, %rax
	movq	%rax, %rbx
	jmp	.L1403
.L1418:
	leaq	.LC0(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7754:
	.size	_ZNSt6vectorISt4pairIjmESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, .-_ZNSt6vectorISt4pairIjmESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.section	.text._ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_,"axG",@progbits,_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_,comdat
	.p2align 4
	.weak	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_
	.type	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_, @function
_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_:
.LFB7831:
	.cfi_startproc
	endbr64
	leaq	8(%rsp), %r10
	.cfi_def_cfa 10, 0
	andq	$-32, %rsp
	pushq	-8(%r10)
	pushq	%rbp
	movq	%rsp, %rbp
	.cfi_escape 0x10,0x6,0x2,0x76,0
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%r10
	.cfi_escape 0xf,0x3,0x76,0x58,0x6
	.cfi_escape 0x10,0xf,0x2,0x76,0x78
	.cfi_escape 0x10,0xe,0x2,0x76,0x70
	.cfi_escape 0x10,0xd,0x2,0x76,0x68
	.cfi_escape 0x10,0xc,0x2,0x76,0x60
	pushq	%rbx
	.cfi_escape 0x10,0x3,0x2,0x76,0x50
	movq	%rsi, %rbx
	addq	$-128, %rsp
	movq	%fs:40, %rax
	movq	%rax, -56(%rbp)
	movq	%rsi, %rax
	subq	%rdi, %rax
	cmpq	$1536, %rax
	jle	.L1419
	movq	%rdi, %r14
	movq	%rdx, %r15
	leaq	96(%rdi), %r13
	movabsq	$-6148914691236517205, %r12
	testq	%rdx, %rdx
	je	.L1422
.L1423:
	movq	%rsi, %rdx
	vmovsd	112(%r14), %xmm1
	decq	%r15
	vmovsd	-80(%rsi), %xmm2
	subq	%r14, %rdx
	sarq	$5, %rdx
	imulq	%r12, %rdx
	movq	%rdx, %rax
	shrq	$63, %rax
	addq	%rdx, %rax
	movq	%rax, %rdx
	andq	$-2, %rax
	sarq	%rdx
	addq	%rdx, %rax
	salq	$5, %rax
	addq	%r14, %rax
	vmovsd	16(%rax), %xmm0
	vcomisd	%xmm0, %xmm1
	jbe	.L1467
	vcomisd	%xmm2, %xmm0
	ja	.L1478
	vcomisd	%xmm2, %xmm1
	vmovdqa	(%r14), %xmm5
	vmovdqa	16(%r14), %xmm4
	vmovdqa	32(%r14), %xmm3
	vmovdqa	48(%r14), %xmm2
	vmovdqa	64(%r14), %xmm1
	vmovdqa	80(%r14), %xmm0
	vmovdqa	%xmm5, -176(%rbp)
	vmovdqa	%xmm4, -160(%rbp)
	vmovdqa	%xmm3, -144(%rbp)
	vmovdqa	%xmm2, -128(%rbp)
	vmovdqa	%xmm1, -112(%rbp)
	vmovdqa	%xmm0, -96(%rbp)
	jbe	.L1477
.L1476:
	vmovdqa	-96(%rsi), %xmm6
	vmovdqa	%xmm6, (%r14)
	vmovdqa	-80(%rsi), %xmm7
	vmovdqa	%xmm7, 16(%r14)
	vmovdqa	-64(%rsi), %xmm6
	vmovdqa	%xmm6, 32(%r14)
	vmovdqa	-48(%rsi), %xmm7
	vmovdqa	%xmm7, 48(%r14)
	vmovdqa	-32(%rsi), %xmm6
	vmovdqa	%xmm6, 64(%r14)
	vmovdqa	-16(%rsi), %xmm7
	vmovdqa	%xmm7, 80(%r14)
	vmovdqa	%xmm5, -96(%rsi)
	vmovdqa	%xmm4, -80(%rsi)
	vmovdqa	%xmm3, -64(%rsi)
	vmovdqa	%xmm2, -48(%rsi)
	vmovdqa	%xmm1, -32(%rsi)
	vmovdqa	%xmm0, -16(%rsi)
.L1432:
	movq	%rsi, %rdx
	movq	%r13, %rbx
	.p2align 4
	.p2align 3
.L1447:
	vmovsd	16(%r14), %xmm0
	vmovsd	16(%rbx), %xmm1
	leaq	96(%rbx), %rax
	vcomisd	%xmm0, %xmm1
	jbe	.L1439
	.p2align 4
	.p2align 3
.L1441:
	movq	%rax, %rbx
	vmovsd	16(%rax), %xmm1
	addq	$96, %rax
	vcomisd	%xmm0, %xmm1
	ja	.L1441
.L1439:
	vcomisd	-80(%rdx), %xmm0
	leaq	-96(%rdx), %rcx
	leaq	-192(%rdx), %rax
	jbe	.L1472
	.p2align 4
	.p2align 3
.L1444:
	movq	%rax, %rdx
	subq	$96, %rax
	vcomisd	112(%rax), %xmm0
	ja	.L1444
	cmpq	%rbx, %rdx
	jbe	.L1479
.L1445:
	vmovdqa	(%rdx), %xmm6
	vmovdqa	(%rbx), %xmm5
	addq	$96, %rbx
	vmovdqa	-80(%rbx), %xmm4
	vmovdqa	-64(%rbx), %xmm3
	vmovdqa	-48(%rbx), %xmm2
	vmovdqa	-32(%rbx), %xmm1
	vmovdqa	-16(%rbx), %xmm0
	vmovdqa	%xmm6, -96(%rbx)
	vmovdqa	16(%rdx), %xmm7
	vmovdqa	%xmm5, -176(%rbp)
	vmovdqa	%xmm4, -160(%rbp)
	vmovdqa	%xmm3, -144(%rbp)
	vmovdqa	%xmm2, -128(%rbp)
	vmovdqa	%xmm1, -112(%rbp)
	vmovdqa	%xmm0, -96(%rbp)
	vmovdqa	%xmm7, -80(%rbx)
	vmovdqa	32(%rdx), %xmm6
	vmovdqa	%xmm6, -64(%rbx)
	vmovdqa	48(%rdx), %xmm7
	vmovdqa	%xmm7, -48(%rbx)
	vmovdqa	64(%rdx), %xmm6
	vmovdqa	%xmm6, -32(%rbx)
	vmovdqa	80(%rdx), %xmm7
	vmovdqa	%xmm7, -16(%rbx)
	vmovdqa	%xmm5, (%rdx)
	vmovdqa	%xmm4, 16(%rdx)
	vmovdqa	%xmm3, 32(%rdx)
	vmovdqa	%xmm2, 48(%rdx)
	vmovdqa	%xmm1, 64(%rdx)
	vmovdqa	%xmm0, 80(%rdx)
	jmp	.L1447
	.p2align 4
	.p2align 3
.L1472:
	movq	%rcx, %rdx
	cmpq	%rbx, %rdx
	ja	.L1445
	.p2align 4
	.p2align 3
.L1479:
	movq	%r15, %rdx
	movq	%rbx, %rdi
	call	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_
	movq	%rbx, %rax
	subq	%r14, %rax
	cmpq	$1536, %rax
	jle	.L1419
	testq	%r15, %r15
	je	.L1422
	movq	%rbx, %rsi
	jmp	.L1423
.L1467:
	vcomisd	%xmm2, %xmm1
	ja	.L1480
	vcomisd	%xmm2, %xmm0
	vmovdqa	(%r14), %xmm5
	vmovdqa	16(%r14), %xmm4
	vmovdqa	32(%r14), %xmm3
	vmovdqa	48(%r14), %xmm2
	vmovdqa	64(%r14), %xmm1
	vmovdqa	80(%r14), %xmm0
	vmovdqa	%xmm5, -176(%rbp)
	vmovdqa	%xmm4, -160(%rbp)
	vmovdqa	%xmm3, -144(%rbp)
	vmovdqa	%xmm2, -128(%rbp)
	vmovdqa	%xmm1, -112(%rbp)
	vmovdqa	%xmm0, -96(%rbp)
	ja	.L1476
.L1471:
	vmovdqa	(%rax), %xmm6
	vmovdqa	%xmm6, (%r14)
	vmovdqa	16(%rax), %xmm7
	vmovdqa	%xmm7, 16(%r14)
	vmovdqa	32(%rax), %xmm6
	vmovdqa	%xmm6, 32(%r14)
	vmovdqa	48(%rax), %xmm7
	vmovdqa	%xmm7, 48(%r14)
	vmovdqa	64(%rax), %xmm6
	vmovdqa	%xmm6, 64(%r14)
	vmovdqa	80(%rax), %xmm7
	vmovdqa	%xmm7, 80(%r14)
	vmovdqa	%xmm5, (%rax)
	vmovdqa	%xmm4, 16(%rax)
	vmovdqa	%xmm3, 32(%rax)
	vmovdqa	%xmm2, 48(%rax)
	vmovdqa	%xmm1, 64(%rax)
	vmovdqa	%xmm0, 80(%rax)
	jmp	.L1432
.L1480:
	vmovdqa	(%r14), %xmm5
	vmovdqa	16(%r14), %xmm4
	vmovdqa	32(%r14), %xmm3
	vmovdqa	48(%r14), %xmm2
	vmovdqa	64(%r14), %xmm1
	vmovdqa	80(%r14), %xmm0
	vmovdqa	%xmm5, -176(%rbp)
	vmovdqa	%xmm4, -160(%rbp)
	vmovdqa	%xmm3, -144(%rbp)
	vmovdqa	%xmm2, -128(%rbp)
	vmovdqa	%xmm1, -112(%rbp)
	vmovdqa	%xmm0, -96(%rbp)
.L1477:
	vmovdqa	96(%r14), %xmm6
	vmovdqa	112(%r14), %xmm7
	vmovdqa	%xmm5, 96(%r14)
	vmovdqa	%xmm4, 112(%r14)
	vmovdqa	%xmm6, (%r14)
	vmovdqa	%xmm7, 16(%r14)
	vmovdqa	128(%r14), %xmm6
	vmovdqa	144(%r14), %xmm7
	vmovdqa	%xmm3, 128(%r14)
	vmovdqa	%xmm2, 144(%r14)
	vmovdqa	%xmm6, 32(%r14)
	vmovdqa	%xmm7, 48(%r14)
	vmovdqa	160(%r14), %xmm6
	vmovdqa	176(%r14), %xmm7
	vmovdqa	%xmm1, 160(%r14)
	vmovdqa	%xmm0, 176(%r14)
	vmovdqa	%xmm6, 64(%r14)
	vmovdqa	%xmm7, 80(%r14)
	jmp	.L1432
.L1422:
	sarq	$5, %rax
	movabsq	$-6148914691236517205, %r12
	imulq	%rax, %r12
	leaq	-2(%r12), %r13
	sarq	%r13
	jmp	.L1426
.L1424:
	decq	%r13
.L1426:
	leaq	0(%r13,%r13,2), %rax
	subq	$96, %rsp
	movq	%r12, %rdx
	movq	%r13, %rsi
	salq	$5, %rax
	movq	%r14, %rdi
	vmovdqa	(%r14,%rax), %xmm0
	vmovdqa	16(%r14,%rax), %xmm1
	vmovdqa	32(%r14,%rax), %xmm2
	vmovdqa	48(%r14,%rax), %xmm3
	vmovdqa	64(%r14,%rax), %xmm4
	vmovdqa	80(%r14,%rax), %xmm5
	vmovdqa	%xmm0, -176(%rbp)
	vmovdqu	%xmm1, 16(%rsp)
	vmovdqu	%xmm0, (%rsp)
	vmovdqu	%xmm3, 48(%rsp)
	vmovdqu	%xmm2, 32(%rsp)
	vmovdqa	%xmm1, -160(%rbp)
	vmovdqu	%xmm5, 80(%rsp)
	vmovdqu	%xmm4, 64(%rsp)
	vmovdqa	%xmm2, -144(%rbp)
	vmovdqa	%xmm3, -128(%rbp)
	vmovdqa	%xmm4, -112(%rbp)
	vmovdqa	%xmm5, -96(%rbp)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_T0_SJ_T1_T2_.isra.0
	addq	$96, %rsp
	testq	%r13, %r13
	jne	.L1424
	subq	$96, %rbx
	movabsq	$-6148914691236517205, %r12
	.p2align 4
	.p2align 3
.L1425:
	vmovdqa	(%r14), %xmm6
	vmovdqa	(%rbx), %xmm0
	movq	%rbx, %r13
	subq	$96, %rsp
	vmovdqa	16(%rbx), %xmm1
	vmovdqa	32(%rbx), %xmm2
	subq	%r14, %r13
	xorl	%esi, %esi
	vmovdqa	48(%rbx), %xmm3
	vmovdqa	64(%rbx), %xmm4
	movq	%r13, %rdx
	movq	%r14, %rdi
	vmovdqa	80(%rbx), %xmm5
	sarq	$5, %rdx
	subq	$96, %rbx
	imulq	%r12, %rdx
	vmovdqa	%xmm6, 96(%rbx)
	vmovdqa	16(%r14), %xmm7
	vmovdqa	%xmm0, -176(%rbp)
	vmovdqa	%xmm1, -160(%rbp)
	vmovdqa	%xmm2, -144(%rbp)
	vmovdqa	%xmm3, -128(%rbp)
	vmovdqa	%xmm4, -112(%rbp)
	vmovdqa	%xmm5, -96(%rbp)
	vmovdqa	%xmm7, 112(%rbx)
	vmovdqa	32(%r14), %xmm6
	vmovdqa	%xmm6, 128(%rbx)
	vmovdqa	48(%r14), %xmm7
	vmovdqa	%xmm7, 144(%rbx)
	vmovdqa	64(%r14), %xmm6
	vmovdqa	%xmm6, 160(%rbx)
	vmovdqa	80(%r14), %xmm7
	vmovdqa	%xmm7, 176(%rbx)
	vmovdqu	%xmm5, 80(%rsp)
	vmovdqu	%xmm4, 64(%rsp)
	vmovdqu	%xmm3, 48(%rsp)
	vmovdqu	%xmm2, 32(%rsp)
	vmovdqu	%xmm1, 16(%rsp)
	vmovdqu	%xmm0, (%rsp)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElS3_NS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_T0_SJ_T1_T2_.isra.0
	addq	$96, %rsp
	cmpq	$96, %r13
	jg	.L1425
.L1419:
	movq	-56(%rbp), %rax
	subq	%fs:40, %rax
	jne	.L1481
	leaq	-48(%rbp), %rsp
	popq	%rbx
	popq	%r10
	.cfi_remember_state
	.cfi_def_cfa 10, 0
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	leaq	-8(%r10), %rsp
	.cfi_def_cfa 7, 8
	ret
.L1478:
	.cfi_restore_state
	vmovdqa	(%r14), %xmm5
	vmovdqa	16(%r14), %xmm4
	vmovdqa	32(%r14), %xmm3
	vmovdqa	48(%r14), %xmm2
	vmovdqa	64(%r14), %xmm1
	vmovdqa	80(%r14), %xmm0
	vmovdqa	%xmm5, -176(%rbp)
	vmovdqa	%xmm4, -160(%rbp)
	vmovdqa	%xmm3, -144(%rbp)
	vmovdqa	%xmm2, -128(%rbp)
	vmovdqa	%xmm1, -112(%rbp)
	vmovdqa	%xmm0, -96(%rbp)
	jmp	.L1471
.L1481:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE7831:
	.size	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_, .-_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_
	.section	.text._ZN11TableSearch5solveERK12TableProblemid,"axG",@progbits,_ZN11TableSearch5solveERK12TableProblemid,comdat
	.align 2
	.p2align 4
	.weak	_ZN11TableSearch5solveERK12TableProblemid
	.type	_ZN11TableSearch5solveERK12TableProblemid, @function
_ZN11TableSearch5solveERK12TableProblemid:
.LFB6150:
	.cfi_startproc
	endbr64
	leaq	8(%rsp), %r10
	.cfi_def_cfa 10, 0
	andq	$-64, %rsp
	pushq	-8(%r10)
	pushq	%rbp
	movq	%rsp, %rbp
	.cfi_escape 0x10,0x6,0x2,0x76,0
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%r10
	.cfi_escape 0xf,0x3,0x76,0x58,0x6
	.cfi_escape 0x10,0xf,0x2,0x76,0x78
	.cfi_escape 0x10,0xe,0x2,0x76,0x70
	.cfi_escape 0x10,0xd,0x2,0x76,0x68
	.cfi_escape 0x10,0xc,0x2,0x76,0x60
	pushq	%rbx
	.cfi_escape 0x10,0x3,0x2,0x76,0x50
	movq	%rdi, %rbx
	subq	$192, %rsp
	vmovd	(%rsi), %xmm5
	vmovsd	%xmm0, -208(%rbp)
	movq	%rsi, %r14
	movq	%fs:40, %rax
	movq	%rax, -56(%rbp)
	xorl	%eax, %eax
	movq	%rsi, 216(%rdi)
	vpinsrd	$1, %edx, %xmm5, %xmm0
	vmovq	%xmm0, 184(%rdi)
	movq	40(%rdi), %rdi
	movslq	4(%rsi), %r12
	movq	56(%rbx), %rsi
	subq	%rdi, %rsi
	movq	%rsi, %rax
	sarq	$2, %rax
	cmpq	%rax, %r12
	ja	.L2058
	movq	48(%rbx), %r13
	movq	%r13, %rdx
	subq	%rdi, %rdx
	movq	%rdx, %r15
	sarq	$2, %r15
	cmpq	%r15, %r12
	jbe	.L1489
	cmpq	%r13, %rdi
	je	.L1493
	xorl	%esi, %esi
	call	memset@PLT
.L1493:
	subq	%r15, %r12
	leaq	0(,%r12,4), %rdx
	leaq	0(%r13,%rdx), %r12
	cmpq	%r12, %r13
	je	.L1492
	xorl	%esi, %esi
	movq	%r13, %rdi
	call	memset@PLT
.L1492:
	movq	%r12, 48(%rbx)
.L1488:
	movq	64(%rbx), %r13
	leaq	64(%rbx), %rdi
	cmpq	%r13, 72(%rbx)
	je	.L1495
	movq	%r13, 72(%rbx)
.L1495:
	movl	184(%rbx), %edx
	testl	%edx, %edx
	jle	.L1690
	movq	%rbx, %rax
	leal	-1(%rdx), %r9d
	subq	%r14, %rax
	addq	$96, %rax
	cmpq	$48, %rax
	jbe	.L1497
	cmpl	$2, %r9d
	jbe	.L1497
	cmpl	$6, %r9d
	jbe	.L1691
	vmovupd	8(%r14), %zmm3
	movl	%edx, %eax
	andl	$-8, %eax
	movl	%eax, %esi
	vmovupd	%zmm3, 112(%rbx)
	cmpl	%eax, %edx
	je	.L1499
	movl	%edx, %r8d
	subl	%eax, %r8d
	leal	-1(%r8), %r10d
	cmpl	$2, %r10d
	jbe	.L1500
.L1498:
	incl	%eax
	salq	$3, %rax
	vmovupd	(%r14,%rax), %ymm3
	vmovupd	%ymm3, 104(%rbx,%rax)
	movl	%r8d, %eax
	andl	$-4, %eax
	addl	%eax, %esi
	cmpl	%eax, %r8d
	je	.L1502
.L1500:
	movslq	%esi, %r8
	leal	1(%rsi), %eax
	salq	$3, %r8
	leaq	(%r14,%r8), %r10
	addq	%rbx, %r8
	vmovsd	8(%r10), %xmm0
	vmovsd	%xmm0, 112(%r8)
	cmpl	%eax, %edx
	jle	.L1502
	vmovsd	16(%r10), %xmm0
	addl	$2, %esi
	vmovsd	%xmm0, 120(%r8)
	cmpl	%esi, %edx
	jle	.L1502
	vmovsd	24(%r10), %xmm0
	vmovsd	%xmm0, 128(%r8)
.L1502:
	vxorpd	%xmm3, %xmm3, %xmm3
	movq	$0x000000000, 176(%rbx)
	cmpl	$6, %r9d
	jbe	.L1736
.L1686:
	vmovupd	72(%r14), %zmm7
	movl	%edx, %r8d
	vmulpd	8(%r14), %zmm7, %zmm1
	andl	$-8, %r8d
	movl	%r8d, %eax
	vunpckhpd	%xmm1, %xmm1, %xmm4
	vextractf64x2	$0x1, %ymm1, %xmm2
	vaddsd	%xmm3, %xmm1, %xmm0
	vextractf64x4	$0x1, %zmm1, %ymm1
	vaddsd	%xmm4, %xmm0, %xmm0
	vaddsd	%xmm2, %xmm0, %xmm0
	vunpckhpd	%xmm2, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vaddsd	%xmm1, %xmm0, %xmm0
	vextractf64x2	$0x1, %ymm1, %xmm1
	vaddsd	%xmm2, %xmm0, %xmm0
	vaddsd	%xmm1, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm1, %xmm0, %xmm0
	cmpl	%edx, %r8d
	je	.L1496
.L1680:
	movl	%edx, %esi
	subl	%r8d, %esi
	leal	-1(%rsi), %r9d
	cmpl	$2, %r9d
	jbe	.L1503
	addl	$9, %r8d
	vmovupd	-64(%r14,%r8,8), %ymm5
	vmulpd	(%r14,%r8,8), %ymm5, %ymm1
	movl	%esi, %r8d
	andl	$-4, %r8d
	addl	%r8d, %eax
	vaddsd	%xmm1, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vextractf64x2	$0x1, %ymm1, %xmm1
	vaddsd	%xmm2, %xmm0, %xmm0
	vaddsd	%xmm1, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm1, %xmm0, %xmm0
	cmpl	%r8d, %esi
	je	.L1496
.L1503:
	movslq	%eax, %r8
	vmovsd	72(%r14,%r8,8), %xmm7
	leaq	(%r14,%r8,8), %rsi
	vfmadd231sd	8(%r14,%r8,8), %xmm7, %xmm0
	leal	1(%rax), %r8d
	cmpl	%r8d, %edx
	jle	.L1496
	vmovsd	80(%rsi), %xmm5
	addl	$2, %eax
	vfmadd231sd	16(%rsi), %xmm5, %xmm0
	cmpl	%eax, %edx
	jle	.L1496
	vmovsd	88(%rsi), %xmm4
	vfmadd231sd	24(%rsi), %xmm4, %xmm0
.L1496:
	movl	4(%r14), %eax
	movq	72(%rbx), %rsi
	vmovsd	%xmm0, 176(%rbx)
	leaq	-176(%rbp), %r12
	testl	%eax, %eax
	jle	.L1505
	vmovq	.LC5(%rip), %xmm5
	vmovsd	.LC25(%rip), %xmm4
	vxorps	%xmm7, %xmm7, %xmm7
	leaq	168(%r14), %r13
	vmovsd	.LC3(%rip), %xmm8
	xorl	%r15d, %r15d
	xorl	%eax, %eax
	leaq	-176(%rbp), %r12
	vmovapd	%xmm5, %xmm6
	jmp	.L1544
	.p2align 4
	.p2align 3
.L2045:
	vcomisd	%xmm1, %xmm3
	jnb	.L1506
	movl	$0, (%rdx)
	movl	184(%rbx), %r8d
	movl	%eax, -176(%rbp)
	vmovsd	%xmm9, -168(%rbp)
	movq	$0x000000000, -160(%rbp)
	testl	%r8d, %r8d
	jle	.L1526
.L1525:
	movl	(%rdx), %ecx
	movl	$1, %edx
	addl	%ecx, %ecx
	subl	%ecx, %edx
	vcvtsi2sdl	%edx, %xmm7, %xmm1
	vmulsd	-8(%r13), %xmm1, %xmm9
	vcomisd	.LC24(%rip), %xmm9
	vandpd	%xmm2, %xmm9, %xmm0
	vmovsd	%xmm9, -144(%rbp)
	seta	%dl
	vmaxsd	%xmm3, %xmm0, %xmm0
	vcomisd	%xmm9, %xmm4
	seta	%cl
	cmpl	$1, %r8d
	je	.L1534
	vmulsd	0(%r13), %xmm1, %xmm9
	vcomisd	.LC24(%rip), %xmm9
	vandpd	%xmm2, %xmm9, %xmm10
	vmovsd	%xmm9, -136(%rbp)
	seta	%r9b
	vmaxsd	%xmm0, %xmm10, %xmm10
	orl	%r9d, %edx
	vcomisd	%xmm9, %xmm4
	seta	%r9b
	orl	%r9d, %ecx
	cmpl	$2, %r8d
	je	.L1701
	vmulsd	8(%r13), %xmm1, %xmm9
	vcomisd	.LC24(%rip), %xmm9
	vandpd	%xmm2, %xmm9, %xmm0
	vmovsd	%xmm9, -128(%rbp)
	seta	%r9b
	vmaxsd	%xmm10, %xmm0, %xmm0
	orl	%r9d, %edx
	vcomisd	%xmm9, %xmm4
	seta	%r9b
	orl	%r9d, %ecx
	cmpl	$3, %r8d
	je	.L1534
	vmulsd	16(%r13), %xmm1, %xmm9
	vcomisd	.LC24(%rip), %xmm9
	vandpd	%xmm2, %xmm9, %xmm10
	vmovsd	%xmm9, -120(%rbp)
	seta	%r9b
	vmaxsd	%xmm0, %xmm10, %xmm10
	orl	%r9d, %edx
	vcomisd	%xmm9, %xmm4
	seta	%r9b
	orl	%r9d, %ecx
	cmpl	$4, %r8d
	je	.L1701
	vmulsd	24(%r13), %xmm1, %xmm9
	vcomisd	.LC24(%rip), %xmm9
	vandpd	%xmm2, %xmm9, %xmm0
	vmovsd	%xmm9, -112(%rbp)
	seta	%r9b
	vmaxsd	%xmm10, %xmm0, %xmm0
	orl	%r9d, %edx
	vcomisd	%xmm9, %xmm4
	seta	%r9b
	orl	%r9d, %ecx
	cmpl	$5, %r8d
	je	.L1534
	vmulsd	32(%r13), %xmm1, %xmm9
	vcomisd	.LC24(%rip), %xmm9
	vandpd	%xmm2, %xmm9, %xmm10
	vmovsd	%xmm9, -104(%rbp)
	seta	%r9b
	vmaxsd	%xmm0, %xmm10, %xmm10
	orl	%r9d, %edx
	vcomisd	%xmm9, %xmm4
	seta	%r9b
	orl	%r9d, %ecx
	cmpl	$6, %r8d
	je	.L1701
	vmulsd	40(%r13), %xmm1, %xmm0
	vcomisd	.LC24(%rip), %xmm0
	vandpd	%xmm2, %xmm0, %xmm9
	vmovsd	%xmm0, -96(%rbp)
	seta	%r9b
	vmaxsd	%xmm10, %xmm9, %xmm9
	orl	%r9d, %edx
	vcomisd	%xmm0, %xmm4
	seta	%r9b
	orl	%r9d, %ecx
	cmpl	$7, %r8d
	je	.L1702
	vmulsd	48(%r13), %xmm1, %xmm1
	vcomisd	.LC24(%rip), %xmm1
	vandpd	%xmm2, %xmm1, %xmm0
	vmovsd	%xmm1, -88(%rbp)
	seta	%r8b
	vmaxsd	%xmm9, %xmm0, %xmm0
	orl	%r8d, %edx
	vcomisd	%xmm1, %xmm4
	seta	%r8b
	orl	%r8d, %ecx
.L1534:
	vmovsd	%xmm0, -160(%rbp)
	testb	%dl, %dl
	je	.L1526
	testb	%cl, %cl
	je	.L1526
	cmpq	%rsi, 80(%rbx)
	je	.L1542
	vmovdqa	-176(%rbp), %xmm2
	addq	$96, %rsi
	vmovdqa	%xmm2, -96(%rsi)
	vmovdqa	-160(%rbp), %xmm2
	vmovdqa	%xmm2, -80(%rsi)
	vmovdqa	-144(%rbp), %xmm1
	vmovdqa	%xmm1, -64(%rsi)
	vmovdqa	-128(%rbp), %xmm2
	vmovdqa	%xmm2, -48(%rsi)
	vmovdqa	-112(%rbp), %xmm1
	vmovdqa	%xmm1, -32(%rsi)
	vmovdqa	-96(%rbp), %xmm2
	vmovdqa	%xmm2, -16(%rsi)
	movq	%rsi, 72(%rbx)
.L1526:
	incl	%eax
	addq	$4, %r15
	addq	$64, %r13
	cmpl	%eax, 4(%r14)
	jle	.L2059
	movl	184(%rbx), %edx
.L1544:
	testl	%edx, %edx
	jle	.L1692
	leal	-1(%rdx), %ecx
	cmpl	$6, %ecx
	jbe	.L1693
	vmovupd	72(%r14), %zmm2
	movl	%edx, %ecx
	vmulpd	-8(%r13), %zmm2, %zmm1
	andl	$-8, %ecx
	movl	%ecx, %r8d
	vunpckhpd	%xmm1, %xmm1, %xmm9
	vextractf64x2	$0x1, %ymm1, %xmm2
	vaddsd	%xmm3, %xmm1, %xmm0
	vextractf64x4	$0x1, %zmm1, %ymm1
	vaddsd	%xmm9, %xmm0, %xmm0
	vaddsd	%xmm2, %xmm0, %xmm0
	vunpckhpd	%xmm2, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vaddsd	%xmm1, %xmm0, %xmm0
	vextractf64x2	$0x1, %ymm1, %xmm1
	vaddsd	%xmm2, %xmm0, %xmm0
	vaddsd	%xmm1, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm1, %xmm0, %xmm0
	cmpl	%ecx, %edx
	je	.L2060
.L1507:
	movl	%edx, %r9d
	subl	%ecx, %r9d
	leal	-1(%r9), %r10d
	cmpl	$2, %r10d
	jbe	.L1509
	vmovupd	72(%r14,%rcx,8), %ymm1
	leaq	20(%rcx,%r15,2), %r10
	movl	%r9d, %ecx
	vmulpd	(%r14,%r10,8), %ymm1, %ymm1
	andl	$-4, %ecx
	addl	%ecx, %r8d
	vaddsd	%xmm1, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm9
	vaddsd	%xmm9, %xmm0, %xmm9
	vextractf64x2	$0x1, %ymm1, %xmm0
	vaddsd	%xmm0, %xmm9, %xmm9
	vunpckhpd	%xmm0, %xmm0, %xmm0
	vaddsd	%xmm0, %xmm9, %xmm0
	cmpl	%ecx, %r9d
	je	.L1510
.L1509:
	movslq	%eax, %rcx
	movslq	%r8d, %r9
	salq	$3, %rcx
	vmovsd	72(%r14,%r9,8), %xmm2
	leaq	(%r14,%r9,8), %r10
	leaq	16(%r9,%rcx), %r11
	leal	1(%r8), %r9d
	vfmadd231sd	32(%r14,%r11,8), %xmm2, %xmm0
	cmpl	%r9d, %edx
	jle	.L1510
	movslq	%r9d, %r9
	vmovsd	80(%r10), %xmm2
	addl	$2, %r8d
	leaq	16(%rcx,%r9), %r9
	vfmadd231sd	32(%r14,%r9,8), %xmm2, %xmm0
	cmpl	%r8d, %edx
	jle	.L1510
	movslq	%r8d, %r8
	vmovsd	88(%r10), %xmm2
	leaq	16(%rcx,%r8), %rcx
	vfmadd231sd	32(%r14,%rcx,8), %xmm2, %xmm0
.L1510:
	vmovsd	-8(%r13), %xmm1
	vmaxsd	%xmm8, %xmm1, %xmm1
.L1511:
	cmpl	$1, %edx
	je	.L1512
.L1685:
	vmovsd	0(%r13), %xmm2
	vmaxsd	%xmm1, %xmm2, %xmm2
	cmpl	$2, %edx
	jle	.L1696
	vmovsd	8(%r13), %xmm1
	vmaxsd	%xmm2, %xmm1, %xmm1
	cmpl	$3, %edx
	je	.L1512
	vmovsd	16(%r13), %xmm2
	vmaxsd	%xmm1, %xmm2, %xmm2
	cmpl	$4, %edx
	je	.L1696
	vmovsd	24(%r13), %xmm1
	vmaxsd	%xmm2, %xmm1, %xmm1
	cmpl	$5, %edx
	je	.L1512
	vmovsd	32(%r13), %xmm2
	vmaxsd	%xmm1, %xmm2, %xmm2
	cmpl	$6, %edx
	je	.L1696
	vmovsd	40(%r13), %xmm9
	vmaxsd	%xmm2, %xmm9, %xmm9
	cmpl	$7, %edx
	je	.L1697
	vmovsd	48(%r13), %xmm1
	vmaxsd	%xmm9, %xmm1, %xmm1
.L1512:
	movq	40(%rbx), %rcx
	vmovapd	%xmm5, %xmm2
	vandpd	%xmm6, %xmm0, %xmm9
	vcomisd	%xmm0, %xmm3
	leaq	(%rcx,%r15), %rdx
	jbe	.L2045
.L2055:
	vaddsd	176(%rbx), %xmm0, %xmm0
	movl	$1, (%rdx)
	movl	184(%rbx), %r8d
	vmovsd	%xmm0, 176(%rbx)
	testl	%r8d, %r8d
	jle	.L1526
	leaq	112(%rbx), %rcx
	movl	%r8d, %r10d
	leal	-1(%r8), %r9d
	subq	%r13, %rcx
	cmpq	$48, %rcx
	jbe	.L1527
	cmpl	$2, %r9d
	jbe	.L1527
	cmpl	$6, %r9d
	jbe	.L1698
	vmovupd	112(%rbx), %zmm1
	movl	%r8d, %ecx
	vaddpd	-8(%r13), %zmm1, %zmm0
	andl	$-8, %ecx
	movl	%ecx, %r9d
	vmovupd	%zmm0, 112(%rbx)
	cmpl	%ecx, %r8d
	je	.L1532
	subl	%ecx, %r10d
	leal	-1(%r10), %r11d
	cmpl	$2, %r11d
	jbe	.L1530
.L1528:
	leaq	112(%rbx,%rcx,8), %r11
	leaq	20(%rcx,%r15,2), %rcx
	vmovupd	(%r11), %ymm2
	vaddpd	(%r14,%rcx,8), %ymm2, %ymm0
	movl	%r10d, %ecx
	andl	$-4, %ecx
	addl	%ecx, %r9d
	vmovupd	%ymm0, (%r11)
	cmpl	%ecx, %r10d
	je	.L1532
.L1530:
	movslq	%r9d, %r11
	movslq	%eax, %r10
	leaq	(%rbx,%r11,8), %rcx
	salq	$3, %r10
	vmovsd	112(%rcx), %xmm0
	leaq	16(%r11,%r10), %r11
	vaddsd	32(%r14,%r11,8), %xmm0, %xmm0
	leal	1(%r9), %r11d
	vmovsd	%xmm0, 112(%rcx)
	cmpl	%r11d, %r8d
	jle	.L1532
	movslq	%r11d, %r11
	vmovsd	120(%rcx), %xmm0
	addl	$2, %r9d
	leaq	16(%r10,%r11), %r11
	vaddsd	32(%r14,%r11,8), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rcx)
	cmpl	%r9d, %r8d
	jle	.L1532
	movslq	%r9d, %r9
	vmovsd	128(%rcx), %xmm0
	leaq	16(%r10,%r9), %r9
	vaddsd	32(%r14,%r9,8), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rcx)
.L1532:
	movl	%eax, -176(%rbp)
	vmovsd	%xmm9, -168(%rbp)
	movq	$0x000000000, -160(%rbp)
	vmovapd	%xmm5, %xmm2
	jmp	.L1525
.L1489:
	movq	%rdi, %r15
	testq	%r12, %r12
	je	.L1494
	leaq	0(,%r12,4), %rdx
	addq	%rdx, %r15
	cmpq	%r15, %rdi
	je	.L1494
	xorl	%esi, %esi
	call	memset@PLT
.L1494:
	cmpq	%r15, %r13
	je	.L1488
	movq	%r15, 48(%rbx)
	jmp	.L1488
	.p2align 4
	.p2align 3
.L1692:
	movq	40(%rbx), %rcx
	vmovsd	%xmm3, %xmm3, %xmm9
	vmovsd	%xmm3, %xmm3, %xmm0
.L1506:
	leaq	(%rcx,%r15), %rdx
	jmp	.L2055
	.p2align 4
	.p2align 3
.L1701:
	vmovsd	%xmm10, %xmm10, %xmm0
	jmp	.L1534
	.p2align 4
	.p2align 3
.L1696:
	vmovsd	%xmm2, %xmm2, %xmm1
	jmp	.L1512
	.p2align 4
	.p2align 3
.L2059:
	movq	64(%rbx), %r13
.L1505:
	movq	%rbx, %rdx
	movq	%r13, %rdi
	vmovsd	%xmm3, -192(%rbp)
	movq	%rsi, -184(%rbp)
	vzeroupper
	call	_ZSt11__remove_ifIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops10_Iter_predIZNS2_5solveERK12TableProblemidEUlRKS3_E_EEET_SI_SI_T0_
	movq	-184(%rbp), %rsi
	vmovsd	-192(%rbp), %xmm3
	movq	%rax, %r14
	cmpq	%rsi, %rax
	je	.L1545
	movq	%rax, 72(%rbx)
.L1545:
	movq	%r14, %rax
	cmpq	%r14, %r13
	je	.L1546
	movq	%r14, %r15
	movabsq	$-6148914691236517205, %rdx
	movq	%r14, %rsi
	movq	%r13, %rdi
	subq	%r13, %r15
	vmovsd	%xmm3, -184(%rbp)
	movq	%r15, %rax
	sarq	$5, %rax
	imulq	%rdx, %rax
	movl	$63, %edx
	lzcntq	%rax, %rax
	subl	%eax, %edx
	movslq	%edx, %rdx
	addq	%rdx, %rdx
	call	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_T1_
	cmpq	$1536, %r15
	vmovsd	-184(%rbp), %xmm3
	jle	.L1547
	leaq	1536(%r13), %r15
	movq	%r13, %rdi
	movq	%r15, %rsi
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_.isra.0
	cmpq	%r14, %r15
	vmovsd	-184(%rbp), %xmm3
	movq	%r15, %rsi
	je	.L1549
	.p2align 4
	.p2align 3
.L1553:
	vmovdqa	(%rsi), %xmm6
	movq	%rsi, %rdx
	leaq	-96(%rsi), %rax
	vmovdqa	%xmm6, -176(%rbp)
	vmovdqa	16(%rsi), %xmm6
	vmovdqa	%xmm6, -160(%rbp)
	vmovdqa	32(%rsi), %xmm6
	vmovdqa	%xmm6, -144(%rbp)
	vmovdqa	48(%rsi), %xmm6
	vmovdqa	%xmm6, -128(%rbp)
	vmovdqa	64(%rsi), %xmm6
	vmovdqa	%xmm6, -112(%rbp)
	vmovdqa	80(%rsi), %xmm6
	vmovdqa	%xmm6, -96(%rbp)
	vmovsd	16(%rsi), %xmm0
	vcomisd	-80(%rsi), %xmm0
	jbe	.L1550
	.p2align 4
	.p2align 3
.L1552:
	vmovdqa	(%rax), %xmm5
	vmovdqa	16(%rax), %xmm7
	movq	%rax, %rdx
	subq	$96, %rax
	vmovdqa	128(%rax), %xmm6
	vmovdqa	160(%rax), %xmm4
	vmovdqa	%xmm5, 192(%rax)
	vmovdqa	%xmm7, 208(%rax)
	vmovdqa	144(%rax), %xmm5
	vmovdqa	176(%rax), %xmm7
	vmovdqa	%xmm6, 224(%rax)
	vmovdqa	%xmm4, 256(%rax)
	vmovdqa	%xmm5, 240(%rax)
	vmovdqa	%xmm7, 272(%rax)
	vcomisd	16(%rax), %xmm0
	ja	.L1552
.L1550:
	vmovdqa	-176(%rbp), %xmm6
	addq	$96, %rsi
	vmovdqa	%xmm6, (%rdx)
	vmovdqa	-160(%rbp), %xmm6
	vmovdqa	%xmm6, 16(%rdx)
	vmovdqa	-144(%rbp), %xmm7
	vmovdqa	%xmm7, 32(%rdx)
	vmovdqa	-128(%rbp), %xmm6
	vmovdqa	%xmm6, 48(%rdx)
	vmovdqa	-112(%rbp), %xmm7
	vmovdqa	%xmm7, 64(%rdx)
	vmovdqa	-96(%rbp), %xmm6
	vmovdqa	%xmm6, 80(%rdx)
	cmpq	%rsi, %r14
	jne	.L1553
.L1549:
	movq	72(%rbx), %r14
	movq	64(%rbx), %rax
.L1546:
	movq	%r14, %rsi
	movabsq	$-6148914691236517205, %r13
	vpxor	%xmm0, %xmm0, %xmm0
	leaq	88(%rbx), %rdi
	subq	%rax, %rsi
	movq	%r12, %rdx
	vmovsd	%xmm3, -184(%rbp)
	vmovdqa	%xmm0, -176(%rbp)
	sarq	$5, %rsi
	vmovdqa	%xmm0, -160(%rbp)
	vmovdqa	%xmm0, -144(%rbp)
	vmovdqa	%xmm0, -128(%rbp)
	imulq	%r13, %rsi
	incq	%rsi
	call	_ZNSt6vectorI6ValuesSaIS0_EE14_M_fill_assignEmRKS0_
	vmovq	64(%rbx), %xmm1
	movq	72(%rbx), %rax
	vmovsd	-184(%rbp), %xmm3
	vmovq	%xmm1, %rdi
	subq	%rdi, %rax
	sarq	$5, %rax
	imulq	%r13, %rax
	movl	%eax, %edx
	decl	%edx
	js	.L1555
	movl	184(%rbx), %r8d
	testl	%r8d, %r8d
	jle	.L1555
	movslq	%edx, %r12
	cltq
	movl	%edx, %edx
	vmovq	%xmm1, %rsi
	subq	%rdx, %rax
	leaq	(%r12,%r12,2), %rcx
	movq	%r12, %rdi
	movl	%r8d, %r10d
	salq	$6, %rax
	movq	%rcx, %r11
	salq	$3, %r12
	salq	$2, %rcx
	addq	$-128, %rax
	salq	$5, %r11
	movq	88(%rbx), %r13
	movq	%rcx, %r15
	movq	%rax, -200(%rbp)
	leal	-1(%r8), %eax
	addq	%rsi, %r11
	vmovq	%rbx, %xmm6
	movl	%eax, -192(%rbp)
	movl	%r8d, %eax
	salq	$6, %rdi
	andl	$-8, %r10d
	shrl	$3, %eax
	vxorpd	%xmm8, %xmm8, %xmm8
	vxorpd	%xmm7, %xmm7, %xmm7
	vmovq	%xmm1, %rcx
	movl	%eax, -184(%rbp)
	movq	%r12, %r14
	movq	%r11, %rbx
	.p2align 4
	.p2align 3
.L1565:
	cmpl	$6, -192(%rbp)
	leaq	64(%r13,%rdi), %rsi
	leaq	0(%r13,%rdi), %r9
	jbe	.L1704
	vmovupd	32(%rbx), %zmm5
	cmpl	$1, -184(%rbp)
	leaq	32(%rbx), %r11
	vcmppd	$1, %zmm7, %zmm5, %k1
	vmovapd	%zmm5, %zmm0{%k1}{z}
	vaddpd	(%rsi), %zmm0, %zmm0
	vmovupd	%zmm0, (%r9)
	jbe	.L1557
	movl	$64, %eax
	movl	$1, %edx
.L1558:
	vmovupd	(%r11,%rax), %zmm4
	incl	%edx
	vcmppd	$1, %zmm7, %zmm4, %k1
	vmovapd	%zmm4, %zmm0{%k1}{z}
	vaddpd	(%rsi,%rax), %zmm0, %zmm0
	vmovupd	%zmm0, -64(%rsi,%rax)
	addq	$64, %rax
	cmpl	%edx, -184(%rbp)
	jne	.L1558
.L1557:
	cmpl	%r10d, %r8d
	je	.L1559
	movl	%r10d, %eax
	movl	%r10d, %edx
.L1556:
	movl	%r8d, %r11d
	subl	%eax, %r11d
	leal	-1(%r11), %r12d
	cmpl	$2, %r12d
	jbe	.L1560
	leaq	8(%rax,%r14), %r12
	leaq	4(%rax,%r15), %rax
	vmovapd	(%rcx,%rax,8), %ymm2
	movl	%r11d, %eax
	andl	$-4, %eax
	addl	%eax, %edx
	vcmpltpd	%ymm8, %ymm2, %ymm0
	vandpd	%ymm2, %ymm0, %ymm0
	vaddpd	0(%r13,%r12,8), %ymm0, %ymm0
	vmovapd	%ymm0, -64(%r13,%r12,8)
	cmpl	%eax, %r11d
	je	.L1559
.L1560:
	movslq	%edx, %rax
	salq	$3, %rax
	leaq	(%rbx,%rax), %r11
	addq	%rax, %rsi
	addq	%rax, %r9
	leal	1(%rdx), %eax
	vmovsd	32(%r11), %xmm0
	vminsd	%xmm3, %xmm0, %xmm0
	vaddsd	(%rsi), %xmm0, %xmm0
	vmovsd	%xmm0, (%r9)
	cmpl	%eax, %r8d
	jle	.L1559
	vmovsd	40(%r11), %xmm0
	addl	$2, %edx
	vminsd	%xmm3, %xmm0, %xmm0
	vaddsd	8(%rsi), %xmm0, %xmm0
	vmovsd	%xmm0, 8(%r9)
	cmpl	%edx, %r8d
	jle	.L1559
	vmovsd	48(%r11), %xmm0
	vminsd	%xmm3, %xmm0, %xmm0
	vaddsd	16(%rsi), %xmm0, %xmm0
	vmovsd	%xmm0, 16(%r9)
.L1559:
	subq	$64, %rdi
	subq	$96, %rbx
	subq	$8, %r14
	subq	$12, %r15
	cmpq	-200(%rbp), %rdi
	jne	.L1565
	vmovq	%xmm6, %rbx
	vzeroupper
.L1555:
	movb	$0, 208(%rbx)
	vmovsd	%xmm3, -184(%rbp)
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	vmovsd	-208(%rbp), %xmm3
	movq	%rax, %r8
	vmulsd	.LC26(%rip), %xmm3, %xmm0
	vmovsd	-184(%rbp), %xmm3
	vcvttsd2siq	%xmm0, %rax
	addq	%r8, %rax
	movq	%rax, 200(%rbx)
	movq	192(%rbx), %rax
	incq	%rax
	testl	$4095, %eax
	movq	%rax, 192(%rbx)
	je	.L2061
.L1566:
	cmpb	$0, 208(%rbx)
	jne	.L1482
	vmovsd	(%rbx), %xmm1
	vaddsd	176(%rbx), %xmm3, %xmm0
	vsubsd	.LC8(%rip), %xmm1, %xmm1
	vcomisd	%xmm1, %xmm0
	jnb	.L1482
	movl	184(%rbx), %eax
	testl	%eax, %eax
	jle	.L1705
	movq	88(%rbx), %rdx
	vmovsd	112(%rbx), %xmm0
	vaddsd	(%rdx), %xmm0, %xmm2
	vcomisd	%xmm1, %xmm2
	jnb	.L1482
	vmovsd	.LC3(%rip), %xmm6
	vmaxsd	%xmm6, %xmm0, %xmm0
	vmovsd	%xmm6, -184(%rbp)
	cmpl	$1, %eax
	je	.L1569
	vmovsd	120(%rbx), %xmm2
	vaddsd	8(%rdx), %xmm2, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L1482
	vcmpltsd	%xmm2, %xmm0, %xmm4
	vblendvpd	%xmm4, %xmm2, %xmm0, %xmm2
	cmpl	$2, %eax
	je	.L1708
	vmovsd	128(%rbx), %xmm0
	vaddsd	16(%rdx), %xmm0, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L1482
	vmaxsd	%xmm2, %xmm0, %xmm2
	cmpl	$3, %eax
	je	.L1708
	vmovsd	136(%rbx), %xmm0
	vaddsd	24(%rdx), %xmm0, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L1482
	vmaxsd	%xmm2, %xmm0, %xmm0
	cmpl	$4, %eax
	je	.L1569
	vmovsd	144(%rbx), %xmm2
	vaddsd	32(%rdx), %xmm2, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L1482
	vmaxsd	%xmm0, %xmm2, %xmm0
	cmpl	$5, %eax
	je	.L1569
	vmovsd	152(%rbx), %xmm2
	vaddsd	40(%rdx), %xmm2, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L1482
	vmaxsd	%xmm0, %xmm2, %xmm0
	cmpl	$6, %eax
	je	.L1569
	vmovsd	160(%rbx), %xmm2
	vaddsd	48(%rdx), %xmm2, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L1482
	vmaxsd	%xmm0, %xmm2, %xmm0
	cmpl	$7, %eax
	je	.L1569
	vmovsd	168(%rbx), %xmm2
	vaddsd	56(%rdx), %xmm2, %xmm4
	vcomisd	%xmm1, %xmm4
	jnb	.L1482
	vmaxsd	%xmm0, %xmm2, %xmm0
.L1569:
	leaq	40(%rbx), %r14
	vcomisd	%xmm0, %xmm1
	ja	.L2062
.L1578:
	movq	64(%rbx), %r13
	movq	72(%rbx), %rax
	movabsq	$-6148914691236517205, %rdi
	subq	%r13, %rax
	sarq	$5, %rax
	imulq	%rdi, %rax
	testl	%eax, %eax
	je	.L1482
	movq	216(%rbx), %rsi
	movslq	0(%r13), %rax
	leaq	112(%rbx), %r15
	vmovsd	%xmm3, -192(%rbp)
	movq	8352(%rsi), %rdi
	movq	40(%rbx), %rsi
	movl	(%rsi,%rax,4), %esi
	cmpl	%esi, (%rdi,%rax,4)
	leaq	40(%r13), %rax
	movq	%r15, %rdi
	setne	-200(%rbp)
	subq	%rax, %rdi
	xorl	%r12d, %r12d
	movq	%rdi, -208(%rbp)
.L1583:
	movl	%r12d, %eax
	xorl	$1, %eax
	cmpb	%al, -200(%rbp)
	jne	.L1580
	vmovsd	-192(%rbp), %xmm3
	vmovsd	8(%r13), %xmm2
	vaddsd	176(%rbx), %xmm3, %xmm1
	vmovsd	(%rbx), %xmm0
	vsubsd	.LC8(%rip), %xmm0, %xmm0
	vaddsd	%xmm2, %xmm1, %xmm1
	vcomisd	%xmm0, %xmm1
	jb	.L2047
.L1643:
	cmpl	$1, %r12d
	jne	.L2063
.L2052:
	vzeroupper
	.p2align 4
	.p2align 3
.L1482:
	movq	-56(%rbp), %rax
	subq	%fs:40, %rax
	jne	.L2064
	addq	$192, %rsp
	popq	%rbx
	popq	%r10
	.cfi_remember_state
	.cfi_def_cfa 10, 0
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	leaq	-8(%r10), %rsp
	.cfi_def_cfa 7, 8
	ret
	.p2align 4
	.p2align 3
.L2060:
	.cfi_restore_state
	vmovsd	-8(%r13), %xmm1
	vcomisd	.LC3(%rip), %xmm1
	ja	.L1685
	movq	.LC3(%rip), %rcx
	vmovq	%rcx, %xmm1
	jmp	.L1511
.L1693:
	xorl	%ecx, %ecx
	xorl	%r8d, %r8d
	vmovsd	%xmm3, %xmm3, %xmm0
	jmp	.L1507
.L1704:
	xorl	%eax, %eax
	xorl	%edx, %edx
	jmp	.L1556
.L1542:
	movq	%r12, %rdx
	movl	%eax, -200(%rbp)
	vmovsd	%xmm3, -192(%rbp)
	movq	%rdi, -184(%rbp)
	vzeroupper
	call	_ZNSt6vectorIN11TableSearch8VariableESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movq	.LC3(%rip), %rdi
	vxorps	%xmm7, %xmm7, %xmm7
	vmovq	.LC5(%rip), %xmm6
	vmovsd	-192(%rbp), %xmm3
	movq	72(%rbx), %rsi
	movl	-200(%rbp), %eax
	vmovq	%rdi, %xmm8
	movq	.LC25(%rip), %rdi
	vmovq	%rdi, %xmm4
	movq	-184(%rbp), %rdi
	vmovapd	%xmm6, %xmm5
	jmp	.L1526
.L1702:
	vmovsd	%xmm9, %xmm9, %xmm0
	jmp	.L1534
.L1697:
	vmovsd	%xmm9, %xmm9, %xmm1
	jmp	.L1512
.L1527:
	vmovsd	112(%rbx), %xmm0
	vaddsd	-8(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 112(%rbx)
	cmpl	$1, %r8d
	je	.L1532
	vmovsd	120(%rbx), %xmm0
	vaddsd	0(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rbx)
	cmpl	$2, %r8d
	je	.L1532
	vmovsd	128(%rbx), %xmm0
	vaddsd	8(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rbx)
	cmpl	$3, %r8d
	je	.L1532
	vmovsd	136(%rbx), %xmm0
	vaddsd	16(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 136(%rbx)
	cmpl	$4, %r8d
	je	.L1532
	vmovsd	144(%rbx), %xmm0
	vaddsd	24(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 144(%rbx)
	cmpl	$5, %r8d
	je	.L1532
	vmovsd	152(%rbx), %xmm0
	vaddsd	32(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 152(%rbx)
	cmpl	$6, %r8d
	je	.L1532
	vmovsd	160(%rbx), %xmm0
	vaddsd	40(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 160(%rbx)
	cmpl	$7, %r8d
	je	.L1532
	vmovsd	168(%rbx), %xmm0
	vaddsd	48(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 168(%rbx)
	jmp	.L1532
.L2058:
	movq	%r12, %rax
	shrq	$61, %rax
	jne	.L2065
	leaq	0(,%r12,4), %r13
	testq	%r12, %r12
	je	.L1688
	movq	%r13, %rdi
	call	_Znwm@PLT
	leaq	(%rax,%r13), %r12
	movq	%rax, %r8
	cmpq	%r12, %rax
	je	.L1486
	xorl	%esi, %esi
	movq	%rax, %rdi
	movq	%r13, %rdx
	call	memset@PLT
	movq	40(%rbx), %rdi
	movq	56(%rbx), %rsi
	movq	%rax, %r8
	subq	%rdi, %rsi
.L1485:
	vmovq	%r8, %xmm5
	movq	%r12, 56(%rbx)
	vpinsrq	$1, %r12, %xmm5, %xmm0
	vmovdqu	%xmm0, 40(%rbx)
	testq	%rdi, %rdi
	je	.L1488
	call	_ZdlPvm@PLT
	jmp	.L1488
.L2061:
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	cmpq	%rax, 200(%rbx)
	vmovsd	-184(%rbp), %xmm3
	jg	.L1566
.L2057:
	movb	$1, 208(%rbx)
	jmp	.L1482
.L1547:
	movq	%r14, %rsi
	movq	%r13, %rdi
	vmovsd	%xmm3, -184(%rbp)
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPN11TableSearch8VariableESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_comp_iterIZNS2_5solveERK12TableProblemidEUlRKS3_SF_E0_EEEvT_SI_T0_.isra.0
	vmovsd	-184(%rbp), %xmm3
	jmp	.L1549
.L1688:
	xorl	%r8d, %r8d
	xorl	%r12d, %r12d
	jmp	.L1485
.L2062:
	movl	188(%rbx), %eax
	vmovsd	%xmm0, (%rbx)
	leaq	16(%rbx), %rdi
	movq	%r14, %rsi
	vmovsd	%xmm3, -192(%rbp)
	movl	%eax, 8(%rbx)
	call	_ZNSt6vectorIiSaIiEEaSERKS1_.isra.0
	vmovsd	-192(%rbp), %xmm3
	jmp	.L1578
.L1497:
	vmovsd	8(%r14), %xmm0
	vmovsd	%xmm0, 112(%rbx)
	cmpl	$1, %edx
	je	.L1502
	vmovsd	16(%r14), %xmm0
	vmovsd	%xmm0, 120(%rbx)
	cmpl	$2, %edx
	je	.L1502
	vmovsd	24(%r14), %xmm0
	vmovsd	%xmm0, 128(%rbx)
	cmpl	$3, %edx
	je	.L1502
	vmovsd	32(%r14), %xmm0
	vmovsd	%xmm0, 136(%rbx)
	cmpl	$4, %edx
	je	.L1502
	vmovsd	40(%r14), %xmm0
	vmovsd	%xmm0, 144(%rbx)
	cmpl	$5, %edx
	je	.L1502
	vmovsd	48(%r14), %xmm0
	vmovsd	%xmm0, 152(%rbx)
	cmpl	$6, %edx
	je	.L1502
	vmovsd	56(%r14), %xmm0
	vmovsd	%xmm0, 160(%rbx)
	cmpl	$7, %edx
	je	.L1502
	vmovsd	64(%r14), %xmm0
	vmovsd	%xmm0, 168(%rbx)
	jmp	.L1502
.L1698:
	xorl	%ecx, %ecx
	xorl	%r9d, %r9d
	jmp	.L1528
.L1580:
	movq	192(%rbx), %rax
	incq	%rax
	movq	%rax, 192(%rbx)
	testl	$4095, %eax
	je	.L2066
.L1641:
	cmpb	$0, 208(%rbx)
	jne	.L2052
	vmovsd	(%rbx), %xmm2
	vmovsd	-192(%rbp), %xmm3
	vsubsd	.LC8(%rip), %xmm2, %xmm2
	vaddsd	176(%rbx), %xmm3, %xmm0
	vcomisd	%xmm2, %xmm0
	jnb	.L1643
	movl	184(%rbx), %edx
	testl	%edx, %edx
	jle	.L1726
	movq	88(%rbx), %rax
	vmovsd	112(%rbx), %xmm0
	vaddsd	64(%rax), %xmm0, %xmm1
	vcomisd	%xmm2, %xmm1
	jnb	.L1643
	vmaxsd	-184(%rbp), %xmm0, %xmm0
	cmpl	$1, %edx
	je	.L1644
	vmovsd	120(%rbx), %xmm1
	vaddsd	72(%rax), %xmm1, %xmm4
	vcomisd	%xmm2, %xmm4
	jnb	.L1643
	vmaxsd	%xmm0, %xmm1, %xmm0
	cmpl	$2, %edx
	je	.L1644
	vmovsd	128(%rbx), %xmm1
	vaddsd	80(%rax), %xmm1, %xmm4
	vcomisd	%xmm2, %xmm4
	jnb	.L1643
	vmaxsd	%xmm0, %xmm1, %xmm0
	cmpl	$3, %edx
	je	.L1644
	vmovsd	136(%rbx), %xmm1
	vaddsd	88(%rax), %xmm1, %xmm4
	vcomisd	%xmm2, %xmm4
	jnb	.L1643
	vmaxsd	%xmm0, %xmm1, %xmm0
	cmpl	$4, %edx
	je	.L1644
	vmovsd	144(%rbx), %xmm1
	vaddsd	96(%rax), %xmm1, %xmm4
	vcomisd	%xmm2, %xmm4
	jnb	.L1643
	vmaxsd	%xmm0, %xmm1, %xmm1
	cmpl	$5, %edx
	je	.L1730
	vmovsd	152(%rbx), %xmm0
	vaddsd	104(%rax), %xmm0, %xmm4
	vcomisd	%xmm2, %xmm4
	jnb	.L1643
	vmaxsd	%xmm1, %xmm0, %xmm0
	cmpl	$6, %edx
	je	.L1644
	vmovsd	160(%rbx), %xmm1
	vaddsd	112(%rax), %xmm1, %xmm4
	vcomisd	%xmm2, %xmm4
	jnb	.L1643
	vmaxsd	%xmm0, %xmm1, %xmm0
	cmpl	$7, %edx
	je	.L1644
	vmovsd	168(%rbx), %xmm1
	vaddsd	120(%rax), %xmm1, %xmm4
	vcomisd	%xmm2, %xmm4
	jnb	.L1643
	vmaxsd	%xmm0, %xmm1, %xmm0
.L1644:
	vcomisd	%xmm0, %xmm2
	ja	.L2067
.L1653:
	movq	64(%rbx), %rax
	movq	72(%rbx), %rdx
	movabsq	$-6148914691236517205, %rdi
	subq	%rax, %rdx
	sarq	$5, %rdx
	imulq	%rdi, %rdx
	cmpl	$1, %edx
	je	.L1655
	movq	216(%rbx), %rcx
	movslq	96(%rax), %rdx
	movl	%r12d, -236(%rbp)
	movl	$0, -216(%rbp)
	movq	%rax, %r12
	movq	8352(%rcx), %rsi
	movq	40(%rbx), %rcx
	movl	(%rcx,%rdx,4), %edi
	cmpl	%edi, (%rsi,%rdx,4)
	leaq	136(%rax), %rdx
	movq	%r15, %rdi
	setne	-232(%rbp)
	subq	%rdx, %rdi
	movq	%rdi, -224(%rbp)
.L1659:
	movzbl	-216(%rbp), %edx
	xorl	$1, %edx
	cmpb	%dl, -232(%rbp)
	jne	.L1656
	vmovsd	-192(%rbp), %xmm3
	vmovsd	104(%r12), %xmm0
	vaddsd	176(%rbx), %xmm3, %xmm2
	vmovsd	(%rbx), %xmm1
	vsubsd	.LC8(%rip), %xmm1, %xmm1
	vaddsd	%xmm0, %xmm2, %xmm2
	vcomisd	%xmm1, %xmm2
	jb	.L2048
.L1679:
	cmpl	$1, -216(%rbp)
	jne	.L2068
	movl	-236(%rbp), %r12d
	movzbl	208(%rbx), %edx
	jmp	.L1640
.L2063:
	movl	$1, %r12d
	jmp	.L1583
.L1690:
	vxorpd	%xmm3, %xmm3, %xmm3
	vmovsd	%xmm3, %xmm3, %xmm0
	jmp	.L1496
.L1736:
	xorl	%r8d, %r8d
	vmovsd	%xmm3, %xmm3, %xmm0
	xorl	%eax, %eax
	jmp	.L1680
.L1499:
	movq	$0x000000000, 176(%rbx)
	vxorpd	%xmm3, %xmm3, %xmm3
	jmp	.L1686
.L1691:
	movl	%edx, %r8d
	xorl	%eax, %eax
	xorl	%esi, %esi
	jmp	.L1498
.L2047:
	movq	40(%rbx), %rax
	movslq	0(%r13), %rdx
	xorl	$1, (%rax,%rdx,4)
	movl	184(%rbx), %eax
	testl	%eax, %eax
	jle	.L1591
	cmpq	$48, -208(%rbp)
	movl	%eax, %esi
	leal	-1(%rax), %edx
	jbe	.L1587
	cmpl	$2, %edx
	jbe	.L1587
	cmpl	$6, %edx
	jbe	.L1714
	vmovupd	112(%rbx), %zmm3
	movl	%eax, %edx
	vaddpd	32(%r13), %zmm3, %zmm0
	andl	$-8, %edx
	movl	%edx, %ecx
	vmovupd	%zmm0, 112(%rbx)
	cmpl	%edx, %eax
	je	.L1591
	subl	%edx, %esi
	leal	-1(%rsi), %edi
	cmpl	$2, %edi
	jbe	.L1592
.L1588:
	addl	$14, %edx
	salq	$3, %rdx
	leaq	(%rbx,%rdx), %rdi
	vmovupd	(%rdi), %ymm3
	vaddpd	-80(%r13,%rdx), %ymm3, %ymm0
	movl	%esi, %edx
	andl	$-4, %edx
	addl	%edx, %ecx
	vmovupd	%ymm0, (%rdi)
	cmpl	%edx, %esi
	je	.L1591
.L1592:
	movslq	%ecx, %rsi
	salq	$3, %rsi
	leaq	(%rbx,%rsi), %rdx
	leaq	0(%r13,%rsi), %rdi
	vmovsd	112(%rdx), %xmm0
	vaddsd	32(%r13,%rsi), %xmm0, %xmm0
	leal	1(%rcx), %esi
	vmovsd	%xmm0, 112(%rdx)
	cmpl	%esi, %eax
	jle	.L1591
	vmovsd	120(%rdx), %xmm0
	addl	$2, %ecx
	vaddsd	40(%rdi), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rdx)
	cmpl	%ecx, %eax
	jle	.L1591
	vmovsd	128(%rdx), %xmm0
	vaddsd	48(%rdi), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rdx)
.L1591:
	movq	192(%rbx), %rdi
	leaq	1(%rdi), %rdx
	movq	%rdx, 192(%rbx)
	testl	$4095, %edx
	je	.L2069
.L1586:
	movzbl	208(%rbx), %edx
	testb	%dl, %dl
	jne	.L1632
	vaddsd	-192(%rbp), %xmm2, %xmm3
	vmovsd	(%rbx), %xmm2
	vsubsd	.LC8(%rip), %xmm2, %xmm2
	vaddsd	176(%rbx), %xmm3, %xmm0
	vmovsd	%xmm3, -216(%rbp)
	vcomisd	%xmm2, %xmm0
	jnb	.L1632
	testl	%eax, %eax
	jle	.L1715
	movq	88(%rbx), %rcx
	vmovsd	112(%rbx), %xmm4
	vaddsd	64(%rcx), %xmm4, %xmm0
	vcomisd	%xmm2, %xmm0
	jnb	.L1598
	vmovsd	-184(%rbp), %xmm5
	vcmpltsd	%xmm4, %xmm5, %xmm0
	vblendvpd	%xmm0, %xmm4, %xmm5, %xmm0
	cmpl	$1, %eax
	je	.L1597
	vmovsd	120(%rbx), %xmm1
	vaddsd	72(%rcx), %xmm1, %xmm5
	vcomisd	%xmm2, %xmm5
	jnb	.L1600
	vmaxsd	%xmm0, %xmm1, %xmm0
	cmpl	$2, %eax
	je	.L1597
	vmovsd	128(%rbx), %xmm5
	vaddsd	80(%rcx), %xmm5, %xmm6
	vcomisd	%xmm2, %xmm6
	jnb	.L1600
	vmaxsd	%xmm0, %xmm5, %xmm0
	cmpl	$3, %eax
	je	.L1597
	vmovsd	136(%rbx), %xmm5
	vaddsd	88(%rcx), %xmm5, %xmm6
	vcomisd	%xmm2, %xmm6
	jnb	.L1600
	vmaxsd	%xmm0, %xmm5, %xmm0
	cmpl	$4, %eax
	je	.L1597
	vmovsd	144(%rbx), %xmm5
	vaddsd	96(%rcx), %xmm5, %xmm6
	vcomisd	%xmm2, %xmm6
	jnb	.L1600
	vmaxsd	%xmm0, %xmm5, %xmm0
	cmpl	$5, %eax
	je	.L1597
	vmovsd	152(%rbx), %xmm5
	vaddsd	104(%rcx), %xmm5, %xmm6
	vcomisd	%xmm2, %xmm6
	jnb	.L1600
	vmaxsd	%xmm0, %xmm5, %xmm0
	cmpl	$6, %eax
	je	.L1597
	vmovsd	160(%rbx), %xmm5
	vaddsd	112(%rcx), %xmm5, %xmm6
	vcomisd	%xmm2, %xmm6
	jnb	.L1600
	vmaxsd	%xmm0, %xmm5, %xmm5
	cmpl	$7, %eax
	je	.L1721
	vmovsd	168(%rbx), %xmm0
	vaddsd	120(%rcx), %xmm0, %xmm6
	vcomisd	%xmm2, %xmm6
	jnb	.L1600
	vmaxsd	%xmm5, %xmm0, %xmm0
.L1597:
	vcomisd	%xmm0, %xmm2
	ja	.L2070
.L1608:
	movq	64(%rbx), %rax
	movq	72(%rbx), %rdx
	movabsq	$-6148914691236517205, %rdi
	movq	40(%rbx), %rcx
	subq	%rax, %rdx
	sarq	$5, %rdx
	imulq	%rdi, %rdx
	cmpl	$1, %edx
	je	.L2056
	movq	216(%rbx), %rsi
	movslq	96(%rax), %rdx
	movl	%r12d, -236(%rbp)
	movl	$0, -224(%rbp)
	movq	%rax, %r12
	movq	8352(%rsi), %rsi
	movl	(%rcx,%rdx,4), %edi
	cmpl	%edi, (%rsi,%rdx,4)
	leaq	136(%rax), %rdx
	movq	%r15, %rdi
	setne	-237(%rbp)
	subq	%rdx, %rdi
	movq	%rdi, -232(%rbp)
.L1631:
	movzbl	-224(%rbp), %edx
	xorl	$1, %edx
	cmpb	%dl, -237(%rbp)
	jne	.L1611
	vmovsd	-216(%rbp), %xmm3
	vmovsd	104(%r12), %xmm0
	vaddsd	176(%rbx), %xmm3, %xmm2
	vmovsd	(%rbx), %xmm1
	vsubsd	.LC8(%rip), %xmm1, %xmm1
	vaddsd	%xmm0, %xmm2, %xmm2
	vcomisd	%xmm1, %xmm2
	jb	.L2071
.L1612:
	cmpl	$1, -224(%rbp)
	jne	.L1724
	movl	-236(%rbp), %r12d
.L2056:
	movl	184(%rbx), %eax
	movzbl	208(%rbx), %edx
.L1632:
	testl	%eax, %eax
	jle	.L1633
.L1598:
	cmpl	$3, %eax
	setg	%cl
	cmpq	$48, -208(%rbp)
	jbe	.L1634
	testb	%cl, %cl
	je	.L1634
.L1683:
	testl	%eax, %eax
	movl	$1, %esi
	cmovg	%eax, %esi
	cmpl	$7, %eax
	jle	.L1725
	vmovupd	(%r15), %zmm3
	movl	%esi, %ecx
	vsubpd	32(%r13), %zmm3, %zmm0
	andl	$-8, %ecx
	movl	%ecx, %edi
	vmovupd	%zmm0, (%r15)
	cmpl	%esi, %ecx
	je	.L1633
.L1635:
	subl	%ecx, %esi
	leal	-1(%rsi), %r8d
	cmpl	$2, %r8d
	jbe	.L1637
	addl	$14, %ecx
	salq	$3, %rcx
	leaq	(%rbx,%rcx), %r8
	vmovupd	(%r8), %ymm3
	vsubpd	-80(%r13,%rcx), %ymm3, %ymm0
	movl	%esi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %edi
	vmovupd	%ymm0, (%r8)
	cmpl	%esi, %ecx
	je	.L1633
.L1637:
	movslq	%edi, %rsi
	salq	$3, %rsi
	leaq	(%rbx,%rsi), %rcx
	leaq	0(%r13,%rsi), %r8
	vmovsd	112(%rcx), %xmm0
	vsubsd	32(%r13,%rsi), %xmm0, %xmm0
	leal	1(%rdi), %esi
	vmovsd	%xmm0, 112(%rcx)
	cmpl	%eax, %esi
	jge	.L1633
	vmovsd	120(%rcx), %xmm0
	addl	$2, %edi
	vsubsd	40(%r8), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rcx)
	cmpl	%eax, %edi
	jge	.L1633
	vmovsd	128(%rcx), %xmm0
	vsubsd	48(%r8), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rcx)
.L1633:
	movslq	0(%r13), %rcx
	movq	40(%rbx), %rax
	xorl	$1, (%rax,%rcx,4)
.L1640:
	testb	%dl, %dl
	je	.L1643
	jmp	.L2052
	.p2align 4
	.p2align 3
.L2069:
	vmovsd	%xmm2, -216(%rbp)
	vzeroupper
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	cmpq	%rax, 200(%rbx)
	jle	.L1595
	vmovsd	-216(%rbp), %xmm2
	movl	184(%rbx), %eax
	jmp	.L1586
.L1486:
	movq	40(%rbx), %rdi
	movq	56(%rbx), %rsi
	subq	%rdi, %rsi
	jmp	.L1485
.L1587:
	vmovsd	112(%rbx), %xmm0
	vaddsd	32(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 112(%rbx)
	cmpl	$1, %eax
	je	.L1591
	vmovsd	120(%rbx), %xmm1
	vaddsd	40(%r13), %xmm1, %xmm1
	vmovsd	%xmm1, 120(%rbx)
	cmpl	$2, %eax
	je	.L1591
	vmovsd	128(%rbx), %xmm0
	vaddsd	48(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rbx)
	cmpl	$3, %eax
	je	.L1591
	vmovsd	136(%rbx), %xmm0
	vaddsd	56(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 136(%rbx)
	cmpl	$4, %eax
	je	.L1591
	vmovsd	144(%rbx), %xmm0
	vaddsd	64(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 144(%rbx)
	cmpl	$5, %eax
	je	.L1591
	vmovsd	152(%rbx), %xmm0
	vaddsd	72(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 152(%rbx)
	cmpl	$6, %eax
	je	.L1591
	vmovsd	160(%rbx), %xmm0
	vaddsd	80(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 160(%rbx)
	cmpl	$7, %eax
	je	.L1591
	vmovsd	168(%rbx), %xmm0
	vaddsd	88(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 168(%rbx)
	jmp	.L1591
.L1634:
	vmovsd	112(%rbx), %xmm0
	vsubsd	32(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 112(%rbx)
	cmpl	$1, %eax
	je	.L1633
	vmovsd	120(%rbx), %xmm1
.L1682:
	vsubsd	40(%r13), %xmm1, %xmm1
	vmovsd	%xmm1, 120(%rbx)
	cmpl	$2, %eax
	je	.L1633
	vmovsd	128(%rbx), %xmm0
	vsubsd	48(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rbx)
	testb	%cl, %cl
	je	.L1633
	vmovsd	136(%rbx), %xmm0
	vsubsd	56(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 136(%rbx)
	cmpl	$4, %eax
	jle	.L1633
	vmovsd	144(%rbx), %xmm0
	vsubsd	64(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 144(%rbx)
	cmpl	$5, %eax
	je	.L1633
	vmovsd	152(%rbx), %xmm0
	vsubsd	72(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 152(%rbx)
	cmpl	$6, %eax
	je	.L1633
	vmovsd	160(%rbx), %xmm0
	vsubsd	80(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 160(%rbx)
	cmpl	$7, %eax
	je	.L1633
	vmovsd	168(%rbx), %xmm0
	vsubsd	88(%r13), %xmm0, %xmm0
	vmovsd	%xmm0, 168(%rbx)
	jmp	.L1633
.L2066:
	vzeroupper
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	cmpq	%rax, 200(%rbx)
	jg	.L1641
	jmp	.L2057
.L1708:
	vmovsd	%xmm2, %xmm2, %xmm0
	jmp	.L1569
.L1705:
	vmovsd	.LC3(%rip), %xmm7
	vmovsd	%xmm7, -184(%rbp)
	vmovsd	%xmm7, %xmm7, %xmm0
	jmp	.L1569
.L2068:
	movl	$1, -216(%rbp)
	jmp	.L1659
.L1656:
	vxorpd	%xmm0, %xmm0, %xmm0
	movl	$2, %esi
	movq	%rbx, %rdi
	vzeroupper
	call	_ZN11TableSearch5visitEid
.L1672:
	cmpb	$0, 208(%rbx)
	je	.L1679
	jmp	.L2052
.L2067:
	movl	188(%rbx), %eax
	leaq	16(%rbx), %rdi
	movq	%r14, %rsi
	vmovsd	%xmm0, (%rbx)
	movl	%eax, 8(%rbx)
	vzeroupper
	call	_ZNSt6vectorIiSaIiEEaSERKS1_.isra.0
	jmp	.L1653
.L1595:
	movl	184(%rbx), %eax
	movb	$1, 208(%rbx)
	movl	$1, %edx
	jmp	.L1632
.L1714:
	xorl	%edx, %edx
	xorl	%ecx, %ecx
	jmp	.L1588
.L2070:
	movl	188(%rbx), %eax
	leaq	16(%rbx), %rdi
	movq	%r14, %rsi
	vmovsd	%xmm0, (%rbx)
	movl	%eax, 8(%rbx)
	vzeroupper
	call	_ZNSt6vectorIiSaIiEEaSERKS1_.isra.0
	jmp	.L1608
.L1725:
	xorl	%ecx, %ecx
	xorl	%edi, %edi
	jmp	.L1635
.L2048:
	movq	40(%rbx), %rdx
	movslq	96(%r12), %rcx
	xorl	$1, (%rdx,%rcx,4)
	movl	184(%rbx), %edx
	testl	%edx, %edx
	jle	.L1668
	cmpq	$48, -224(%rbp)
	movl	%edx, %edi
	leal	-1(%rdx), %ecx
	jbe	.L1664
	cmpl	$2, %ecx
	jbe	.L1664
	cmpl	$6, %ecx
	jbe	.L1734
	vmovupd	112(%rbx), %zmm3
	movl	%edx, %ecx
	vaddpd	128(%r12), %zmm3, %zmm1
	andl	$-8, %ecx
	movl	%ecx, %esi
	vmovupd	%zmm1, 112(%rbx)
	cmpl	%ecx, %edx
	je	.L1668
	subl	%ecx, %edi
	leal	-1(%rdi), %r8d
	cmpl	$2, %r8d
	jbe	.L1669
.L1665:
	addl	$14, %ecx
	salq	$3, %rcx
	leaq	(%rbx,%rcx), %r8
	vmovupd	(%r8), %ymm3
	vaddpd	16(%r12,%rcx), %ymm3, %ymm1
	movl	%edi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %esi
	vmovupd	%ymm1, (%r8)
	cmpl	%edi, %ecx
	je	.L1668
.L1669:
	movslq	%esi, %rdi
	salq	$3, %rdi
	leaq	(%rbx,%rdi), %rcx
	leaq	(%r12,%rdi), %r8
	vmovsd	112(%rcx), %xmm1
	vaddsd	128(%r12,%rdi), %xmm1, %xmm1
	leal	1(%rsi), %edi
	vmovsd	%xmm1, 112(%rcx)
	cmpl	%edi, %edx
	jle	.L1668
	vmovsd	120(%rcx), %xmm1
	addl	$2, %esi
	vaddsd	136(%r8), %xmm1, %xmm1
	vmovsd	%xmm1, 120(%rcx)
	cmpl	%esi, %edx
	jle	.L1668
	vmovsd	128(%rcx), %xmm1
	vaddsd	144(%r8), %xmm1, %xmm1
	vmovsd	%xmm1, 128(%rcx)
.L1668:
	vaddsd	-192(%rbp), %xmm0, %xmm0
	movl	$2, %esi
	movq	%rbx, %rdi
	vzeroupper
	call	_ZN11TableSearch5visitEid
	movl	184(%rbx), %edx
	testl	%edx, %edx
	jle	.L1663
	cmpq	$48, -224(%rbp)
	movl	%edx, %edi
	leal	-1(%rdx), %ecx
	jbe	.L1673
	cmpl	$2, %ecx
	jbe	.L1673
	cmpl	$6, %ecx
	jbe	.L1735
	vmovupd	112(%rbx), %zmm3
	movl	%edx, %ecx
	vsubpd	128(%r12), %zmm3, %zmm0
	andl	$-8, %ecx
	movl	%ecx, %esi
	vmovupd	%zmm0, 112(%rbx)
	cmpl	%ecx, %edx
	je	.L1663
	subl	%ecx, %edi
	leal	-1(%rdi), %r8d
	cmpl	$2, %r8d
	jbe	.L1676
.L1674:
	addl	$14, %ecx
	salq	$3, %rcx
	leaq	(%rbx,%rcx), %r8
	vmovupd	(%r8), %ymm3
	vsubpd	16(%r12,%rcx), %ymm3, %ymm0
	movl	%edi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %esi
	vmovupd	%ymm0, (%r8)
	cmpl	%edi, %ecx
	je	.L1663
.L1676:
	movslq	%esi, %rdi
	salq	$3, %rdi
	leaq	(%rbx,%rdi), %rcx
	leaq	(%r12,%rdi), %r8
	vmovsd	112(%rcx), %xmm0
	vsubsd	128(%r12,%rdi), %xmm0, %xmm0
	leal	1(%rsi), %edi
	vmovsd	%xmm0, 112(%rcx)
	cmpl	%edi, %edx
	jle	.L1663
	vmovsd	120(%rcx), %xmm0
	addl	$2, %esi
	vsubsd	136(%r8), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rcx)
	cmpl	%esi, %edx
	jle	.L1663
	vmovsd	128(%rcx), %xmm0
	vsubsd	144(%r8), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rcx)
.L1663:
	movslq	96(%r12), %rcx
	movq	40(%rbx), %rdx
	xorl	$1, (%rdx,%rcx,4)
	jmp	.L1672
.L1655:
	movzbl	208(%rbx), %edx
	jmp	.L1640
.L1600:
	cmpl	$3, %eax
	setg	%cl
	cmpq	$48, -208(%rbp)
	seta	%sil
	testb	%cl, %sil
	jne	.L1683
	vsubsd	32(%r13), %xmm4, %xmm4
	xorl	%edx, %edx
	vmovsd	%xmm4, 112(%rbx)
	jmp	.L1682
.L1724:
	movl	$1, -224(%rbp)
	jmp	.L1631
.L2071:
	movq	40(%rbx), %rdx
	movslq	96(%r12), %rcx
	xorl	$1, (%rdx,%rcx,4)
	movl	184(%rbx), %edx
	testl	%edx, %edx
	jle	.L1620
	cmpq	$48, -232(%rbp)
	movl	%edx, %edi
	leal	-1(%rdx), %ecx
	jbe	.L1616
	cmpl	$2, %ecx
	jbe	.L1616
	cmpl	$6, %ecx
	jbe	.L1722
	vmovupd	128(%r12), %zmm3
	movl	%edx, %ecx
	vaddpd	112(%rbx), %zmm3, %zmm1
	andl	$-8, %ecx
	movl	%ecx, %esi
	vmovupd	%zmm1, 112(%rbx)
	cmpl	%edx, %ecx
	je	.L1620
	subl	%ecx, %edi
	leal	-1(%rdi), %r8d
	cmpl	$2, %r8d
	jbe	.L1621
.L1617:
	addl	$14, %ecx
	salq	$3, %rcx
	leaq	(%rbx,%rcx), %r8
	vmovupd	(%r8), %ymm3
	vaddpd	16(%r12,%rcx), %ymm3, %ymm1
	movl	%edi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %esi
	vmovupd	%ymm1, (%r8)
	cmpl	%edi, %ecx
	je	.L1620
.L1621:
	movslq	%esi, %rdi
	salq	$3, %rdi
	leaq	(%rbx,%rdi), %rcx
	leaq	(%r12,%rdi), %r8
	vmovsd	112(%rcx), %xmm1
	vaddsd	128(%r12,%rdi), %xmm1, %xmm1
	leal	1(%rsi), %edi
	vmovsd	%xmm1, 112(%rcx)
	cmpl	%edx, %edi
	jge	.L1620
	vmovsd	120(%rcx), %xmm1
	addl	$2, %esi
	vaddsd	136(%r8), %xmm1, %xmm1
	vmovsd	%xmm1, 120(%rcx)
	cmpl	%edx, %esi
	jge	.L1620
	vmovsd	128(%rcx), %xmm1
	vaddsd	144(%r8), %xmm1, %xmm1
	vmovsd	%xmm1, 128(%rcx)
.L1620:
	vaddsd	-216(%rbp), %xmm0, %xmm0
	movl	$2, %esi
	movq	%rbx, %rdi
	vzeroupper
	call	_ZN11TableSearch5visitEid
	movl	184(%rbx), %edx
	testl	%edx, %edx
	jle	.L1615
	cmpq	$48, -232(%rbp)
	movl	%edx, %edi
	leal	-1(%rdx), %ecx
	jbe	.L1625
	cmpl	$2, %ecx
	jbe	.L1625
	cmpl	$6, %ecx
	jbe	.L1723
	vmovupd	112(%rbx), %zmm3
	movl	%edx, %ecx
	vsubpd	128(%r12), %zmm3, %zmm0
	andl	$-8, %ecx
	movl	%ecx, %esi
	vmovupd	%zmm0, 112(%rbx)
	cmpl	%edx, %ecx
	je	.L1615
	subl	%ecx, %edi
	leal	-1(%rdi), %r8d
	cmpl	$2, %r8d
	jbe	.L1628
.L1626:
	addl	$14, %ecx
	salq	$3, %rcx
	leaq	(%rbx,%rcx), %r8
	vmovupd	(%r8), %ymm3
	vsubpd	16(%r12,%rcx), %ymm3, %ymm0
	movl	%edi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %esi
	vmovupd	%ymm0, (%r8)
	cmpl	%edi, %ecx
	je	.L1615
.L1628:
	movslq	%esi, %rdi
	salq	$3, %rdi
	leaq	(%rbx,%rdi), %rcx
	leaq	(%r12,%rdi), %r8
	vmovsd	112(%rcx), %xmm0
	vsubsd	128(%r12,%rdi), %xmm0, %xmm0
	leal	1(%rsi), %edi
	vmovsd	%xmm0, 112(%rcx)
	cmpl	%edx, %edi
	jge	.L1615
	vmovsd	120(%rcx), %xmm0
	addl	$2, %esi
	vsubsd	136(%r8), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rcx)
	cmpl	%edx, %esi
	jge	.L1615
	vmovsd	128(%rcx), %xmm0
	vsubsd	144(%r8), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rcx)
.L1615:
	movslq	96(%r12), %rcx
	movq	40(%rbx), %rdx
	xorl	$1, (%rdx,%rcx,4)
.L1624:
	movzbl	208(%rbx), %edx
	testb	%dl, %dl
	je	.L1612
	movl	-236(%rbp), %r12d
	movl	184(%rbx), %eax
	jmp	.L1632
.L1611:
	vmovsd	-216(%rbp), %xmm0
	movl	$2, %esi
	movq	%rbx, %rdi
	vzeroupper
	call	_ZN11TableSearch5visitEid
	jmp	.L1624
.L1723:
	xorl	%esi, %esi
	xorl	%ecx, %ecx
	jmp	.L1626
.L1625:
	vmovsd	112(%rbx), %xmm0
	vsubsd	128(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 112(%rbx)
	cmpl	$1, %edx
	je	.L1615
	vmovsd	120(%rbx), %xmm0
	vsubsd	136(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rbx)
	cmpl	$2, %edx
	je	.L1615
	vmovsd	128(%rbx), %xmm0
	vsubsd	144(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rbx)
	cmpl	$3, %edx
	je	.L1615
	vmovsd	136(%rbx), %xmm0
	vsubsd	152(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 136(%rbx)
	cmpl	$4, %edx
	je	.L1615
	vmovsd	144(%rbx), %xmm0
	vsubsd	160(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 144(%rbx)
	cmpl	$5, %edx
	je	.L1615
	vmovsd	152(%rbx), %xmm0
	vsubsd	168(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 152(%rbx)
	cmpl	$6, %edx
	je	.L1615
	vmovsd	160(%rbx), %xmm0
	vsubsd	176(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 160(%rbx)
	cmpl	$7, %edx
	je	.L1615
	vmovsd	168(%rbx), %xmm0
	vsubsd	184(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 168(%rbx)
	jmp	.L1615
.L1722:
	xorl	%esi, %esi
	xorl	%ecx, %ecx
	jmp	.L1617
.L1616:
	vmovsd	112(%rbx), %xmm1
	vaddsd	128(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 112(%rbx)
	cmpl	$1, %edx
	je	.L1620
	vmovsd	120(%rbx), %xmm1
	vaddsd	136(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 120(%rbx)
	cmpl	$2, %edx
	je	.L1620
	vmovsd	128(%rbx), %xmm1
	vaddsd	144(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 128(%rbx)
	cmpl	$3, %edx
	je	.L1620
	vmovsd	136(%rbx), %xmm1
	vaddsd	152(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 136(%rbx)
	cmpl	$4, %edx
	je	.L1620
	vmovsd	144(%rbx), %xmm1
	vaddsd	160(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 144(%rbx)
	cmpl	$5, %edx
	je	.L1620
	vmovsd	152(%rbx), %xmm1
	vaddsd	168(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 152(%rbx)
	cmpl	$6, %edx
	je	.L1620
	vmovsd	160(%rbx), %xmm1
	vaddsd	176(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 160(%rbx)
	cmpl	$7, %edx
	je	.L1620
	vmovsd	168(%rbx), %xmm1
	vaddsd	184(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 168(%rbx)
	jmp	.L1620
.L1721:
	vmovsd	%xmm5, %xmm5, %xmm0
	jmp	.L1597
.L1715:
	vmovsd	-184(%rbp), %xmm0
	jmp	.L1597
.L1734:
	xorl	%ecx, %ecx
	xorl	%esi, %esi
	jmp	.L1665
.L1664:
	vmovsd	112(%rbx), %xmm1
	vaddsd	128(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 112(%rbx)
	cmpl	$1, %edx
	je	.L1668
	vmovsd	120(%rbx), %xmm1
	vaddsd	136(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 120(%rbx)
	cmpl	$2, %edx
	je	.L1668
	vmovsd	128(%rbx), %xmm1
	vaddsd	144(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 128(%rbx)
	cmpl	$3, %edx
	je	.L1668
	vmovsd	136(%rbx), %xmm1
	vaddsd	152(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 136(%rbx)
	cmpl	$4, %edx
	je	.L1668
	vmovsd	144(%rbx), %xmm1
	vaddsd	160(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 144(%rbx)
	cmpl	$5, %edx
	je	.L1668
	vmovsd	152(%rbx), %xmm1
	vaddsd	168(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 152(%rbx)
	cmpl	$6, %edx
	je	.L1668
	vmovsd	160(%rbx), %xmm1
	vaddsd	176(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 160(%rbx)
	cmpl	$7, %edx
	je	.L1668
	vmovsd	168(%rbx), %xmm1
	vaddsd	184(%r12), %xmm1, %xmm1
	vmovsd	%xmm1, 168(%rbx)
	jmp	.L1668
.L2064:
	call	__stack_chk_fail@PLT
.L2065:
	leaq	.LC11(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
.L1735:
	xorl	%ecx, %ecx
	xorl	%esi, %esi
	jmp	.L1674
.L1673:
	vmovsd	112(%rbx), %xmm0
	vsubsd	128(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 112(%rbx)
	cmpl	$1, %edx
	je	.L1663
	vmovsd	120(%rbx), %xmm0
	vsubsd	136(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 120(%rbx)
	cmpl	$2, %edx
	je	.L1663
	vmovsd	128(%rbx), %xmm0
	vsubsd	144(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 128(%rbx)
	cmpl	$3, %edx
	je	.L1663
	vmovsd	136(%rbx), %xmm0
	vsubsd	152(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 136(%rbx)
	cmpl	$4, %edx
	je	.L1663
	vmovsd	144(%rbx), %xmm0
	vsubsd	160(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 144(%rbx)
	cmpl	$5, %edx
	je	.L1663
	vmovsd	152(%rbx), %xmm0
	vsubsd	168(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 152(%rbx)
	cmpl	$6, %edx
	je	.L1663
	vmovsd	160(%rbx), %xmm0
	vsubsd	176(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 160(%rbx)
	cmpl	$7, %edx
	je	.L1663
	vmovsd	168(%rbx), %xmm0
	vsubsd	184(%r12), %xmm0, %xmm0
	vmovsd	%xmm0, 168(%rbx)
	jmp	.L1663
.L1730:
	vmovsd	%xmm1, %xmm1, %xmm0
	jmp	.L1644
.L1726:
	vmovsd	-184(%rbp), %xmm0
	jmp	.L1644
	.cfi_endproc
.LFE6150:
	.size	_ZN11TableSearch5solveERK12TableProblemid, .-_ZN11TableSearch5solveERK12TableProblemid
	.section	.rodata._ZN11TableSearch3runEd.str1.1,"aMS",@progbits,1
.LC28:
	.string	"{\"candidate\":"
.LC30:
	.string	",\"score\":"
.LC31:
	.string	",\"correction\":["
.LC32:
	.string	"]}\n"
.LC33:
	.string	","
.LC34:
	.string	"table_nodes="
.LC35:
	.string	" polished="
.LC36:
	.string	"\n"
	.section	.text._ZN11TableSearch3runEd,"axG",@progbits,_ZN11TableSearch3runEd,comdat
	.align 2
	.p2align 4
	.weak	_ZN11TableSearch3runEd
	.type	_ZN11TableSearch3runEd, @function
_ZN11TableSearch3runEd:
.LFB6155:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA6155
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	leaq	_ZSt3cin(%rip), %r13
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	vmovq	%xmm0, %rbx
	subq	$88, %rsp
	.cfi_def_cfa_offset 144
	movq	%rdi, 8(%rsp)
	movq	%fs:40, %rax
	movq	%rax, 72(%rsp)
	xorl	%eax, %eax
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	vmovq	%rbx, %xmm7
	vmulsd	.LC26(%rip), %xmm7, %xmm0
	leaq	68(%rsp), %rsi
	movq	%r13, %rdi
	vcvttsd2siq	%xmm0, %rdx
	addq	%rdx, %rax
	movq	%rax, 40(%rsp)
.LEHB0:
	call	_ZNSirsERi@PLT
	movslq	68(%rsp), %rax
	movabsq	$1100115939510350, %rdx
	cmpq	%rdx, %rax
	ja	.L2155
	imulq	$8384, %rax, %rbx
	testq	%rax, %rax
	je	.L2120
	movq	%rbx, %rdi
	movl	$32, %esi
	call	_ZnwmSt11align_val_t@PLT
.LEHE0:
	addq	%rax, %rbx
	movq	%rax, %rcx
	movq	%rax, 48(%rsp)
	movq	%rbx, 32(%rsp)
	.p2align 4
	.p2align 3
.L2075:
	movq	%rcx, %rdi
	movl	$8384, %edx
	xorl	%esi, %esi
	call	memset@PLT
	vpxor	%xmm6, %xmm6, %xmm6
	movq	%rax, %rcx
	vmovdqu	%xmm6, 8352(%rax)
	addq	$8384, %rcx
	cmpq	%rcx, %rbx
	jne	.L2075
	movl	68(%rsp), %eax
	testl	%eax, %eax
	jle	.L2074
	movq	8(%rsp), %rax
	movq	48(%rsp), %r12
	movl	$0, 16(%rsp)
	addq	$16, %rax
	movq	%r12, 24(%rsp)
	movq	%rax, 56(%rsp)
	.p2align 4
	.p2align 3
.L2099:
	movq	%r12, %rsi
	movq	%r13, %rdi
.LEHB1:
	call	_ZNSirsERi@PLT
	movq	%rax, %rdi
	leaq	4(%r12), %rsi
	call	_ZNSirsERi@PLT
	movl	(%r12), %eax
	testl	%eax, %eax
	jle	.L2078
	leaq	8(%r12), %rbp
	xorl	%ebx, %ebx
	.p2align 4
	.p2align 3
.L2079:
	movq	%rbp, %rsi
	movq	%r13, %rdi
	call	_ZNSi10_M_extractIdEERSiRT_@PLT
	movl	(%r12), %eax
	incl	%ebx
	addq	$8, %rbp
	cmpl	%ebx, %eax
	jg	.L2079
	movslq	4(%r12), %rsi
	testl	%esi, %esi
	jle	.L2081
.L2080:
	leaq	160(%r12), %r14
	xorl	%r15d, %r15d
	testl	%eax, %eax
	jle	.L2084
	.p2align 4
	.p2align 3
.L2121:
	movq	%r14, %rbp
	xorl	%ebx, %ebx
	.p2align 4
	.p2align 3
.L2082:
	movq	%rbp, %rsi
	movq	%r13, %rdi
	call	_ZNSi10_M_extractIdEERSiRT_@PLT
	movl	(%r12), %eax
	incl	%ebx
	addq	$8, %rbp
	cmpl	%ebx, %eax
	jg	.L2082
	movslq	4(%r12), %rsi
	leal	1(%r15), %edx
	cmpl	%esi, %edx
	jge	.L2081
	incq	%r15
	addq	$64, %r14
	testl	%eax, %eax
	jg	.L2121
.L2084:
	movq	8360(%r12), %rbp
	movq	8352(%r12), %rbx
	leaq	8352(%r12), %r14
	movq	%rbp, %rax
	subq	%rbx, %rax
	sarq	$2, %rax
	cmpq	%rax, %rsi
	ja	.L2156
	jnb	.L2154
	leaq	(%rbx,%rsi,4), %rax
	cmpq	%rax, %rbp
	je	.L2154
	movq	%rax, 8360(%r12)
	movq	%rax, %rbp
	jmp	.L2154
	.p2align 4
	.p2align 3
.L2091:
	movq	%rbx, %rsi
	movq	%r13, %rdi
	call	_ZNSirsERi@PLT
	addq	$4, %rbx
.L2154:
	cmpq	%rbx, %rbp
	jne	.L2091
	movl	(%r12), %edx
	vmovsd	.LC3(%rip), %xmm2
	testl	%edx, %edx
	jle	.L2090
	movl	4(%r12), %r8d
	vmovsd	.LC3(%rip), %xmm2
	leaq	160(%r12), %rsi
	leal	-1(%r8), %eax
	salq	$6, %rax
	leaq	224(%r12,%rax), %rcx
	leal	-1(%rdx), %eax
	leaq	168(%r12,%rax,8), %rdi
	.p2align 4
	.p2align 3
.L2096:
	vmovsd	-152(%rsi), %xmm1
	testl	%r8d, %r8d
	jle	.L2093
	movq	8352(%r12), %rdx
	movq	%rsi, %rax
	.p2align 4
	.p2align 3
.L2094:
	vxorpd	%xmm3, %xmm3, %xmm3
	addq	$64, %rax
	addq	$4, %rdx
	vcvtsi2sdl	-4(%rdx), %xmm3, %xmm0
	vmulsd	-64(%rax), %xmm0, %xmm0
	vaddsd	%xmm0, %xmm1, %xmm1
	cmpq	%rax, %rcx
	jne	.L2094
.L2093:
	addq	$8, %rsi
	vmaxsd	%xmm2, %xmm1, %xmm2
	addq	$8, %rcx
	cmpq	%rsi, %rdi
	jne	.L2096
.L2090:
	movq	8(%rsp), %rax
	vmovsd	(%rax), %xmm0
	vcomisd	%xmm2, %xmm0
	ja	.L2157
.L2097:
	incl	16(%rsp)
	movl	68(%rsp), %eax
	addq	$8384, %r12
	movl	16(%rsp), %ecx
	cmpl	%ecx, %eax
	jg	.L2099
	testl	%eax, %eax
	jle	.L2074
	xorl	%ebx, %ebx
	jmp	.L2101
	.p2align 4
	.p2align 3
.L2158:
	vminsd	.LC27(%rip), %xmm0, %xmm0
	movq	24(%rsp), %rsi
	movl	%ebx, %edx
	movq	8(%rsp), %rdi
	call	_ZN11TableSearch5solveERK12TableProblemid
	addq	$8384, 24(%rsp)
	incl	%ebx
	cmpl	%ebx, 68(%rsp)
	jle	.L2074
.L2101:
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	vxorpd	%xmm4, %xmm4, %xmm4
	vmovsd	.LC29(%rip), %xmm5
	movq	%rax, %r8
	movq	40(%rsp), %rax
	subq	%r8, %rax
	vcvtsi2sdq	%rax, %xmm4, %xmm0
	vdivsd	.LC26(%rip), %xmm0, %xmm0
	vcomisd	%xmm0, %xmm5
	jbe	.L2158
.L2074:
	leaq	_ZSt4cout(%rip), %rbp
	movl	$13, %edx
	leaq	.LC28(%rip), %rsi
	movq	%rbp, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	8(%rsp), %rbx
	movq	%rbp, %rdi
	movl	8(%rbx), %esi
	call	_ZNSolsEi@PLT
	movl	$9, %edx
	leaq	.LC30(%rip), %rsi
	movq	%rax, %rdi
	movq	%rax, %r12
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	(%r12), %rax
	vmovsd	(%rbx), %xmm0
	movq	%r12, %rdi
	movq	-24(%rax), %rax
	movq	$15, 8(%r12,%rax)
	call	_ZNSo9_M_insertIdEERSoT_@PLT
	movq	%rax, %rdi
	movl	$15, %edx
	leaq	.LC31(%rip), %rsi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	%rbx, %rax
	movq	16(%rbx), %rdx
	leaq	.LC33(%rip), %r12
	xorl	%ebx, %ebx
	cmpq	24(%rax), %rdx
	je	.L2106
.L2102:
	movl	(%rdx,%rbx,4), %esi
	movq	%rbp, %rdi
	call	_ZNSolsEi@PLT
.L2159:
	movq	8(%rsp), %rax
	incq	%rbx
	movq	16(%rax), %rdx
	movq	24(%rax), %rax
	movq	%rax, 16(%rsp)
	subq	%rdx, %rax
	sarq	$2, %rax
	cmpq	%rax, %rbx
	jnb	.L2106
	testq	%rbx, %rbx
	je	.L2102
	movl	$1, %edx
	movq	%r12, %rsi
	movq	%rbp, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	8(%rsp), %rax
	movq	%rbp, %rdi
	movq	16(%rax), %rdx
	movl	(%rdx,%rbx,4), %esi
	call	_ZNSolsEi@PLT
	jmp	.L2159
	.p2align 4
	.p2align 3
.L2081:
	testl	%eax, %eax
	jle	.L2084
	leaq	72(%r12), %rbp
	xorl	%ebx, %ebx
	.p2align 4
	.p2align 3
.L2085:
	movq	%rbp, %rsi
	movq	%r13, %rdi
	call	_ZNSi10_M_extractIdEERSiRT_@PLT
	incl	%ebx
	addq	$8, %rbp
	cmpl	%ebx, (%r12)
	jg	.L2085
	movslq	4(%r12), %rsi
	jmp	.L2084
.L2157:
	movl	16(%rsp), %ecx
	movq	56(%rsp), %rdi
	vmovsd	%xmm2, (%rax)
	movq	%r14, %rsi
	movl	%ecx, 8(%rax)
	call	_ZNSt6vectorIiSaIiEEaSERKS1_.isra.0
	jmp	.L2097
.L2156:
	subq	%rax, %rsi
	movq	%r14, %rdi
	call	_ZNSt6vectorIiSaIiEE17_M_default_appendEm
	movq	8360(%r12), %rbp
	movq	8352(%r12), %rbx
	jmp	.L2154
.L2106:
	movl	$3, %edx
	leaq	.LC32(%rip), %rsi
	movq	%rbp, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	leaq	_ZSt4cerr(%rip), %rbp
	movl	$12, %edx
	leaq	.LC34(%rip), %rsi
	movq	%rbp, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	8(%rsp), %rbx
	movq	%rbp, %rdi
	movq	192(%rbx), %rsi
	call	_ZNSo9_M_insertImEERSoT_@PLT
	movl	$10, %edx
	leaq	.LC35(%rip), %rsi
	movq	%rax, %rdi
	movq	%rax, %rbp
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	vmovsd	(%rbx), %xmm0
	movq	%rbp, %rdi
	call	_ZNSo9_M_insertIdEERSoT_@PLT
	movq	%rax, %rdi
	movl	$1, %edx
	leaq	.LC36(%rip), %rsi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
.LEHE1:
	movq	48(%rsp), %rax
	movq	32(%rsp), %rcx
	movq	%rax, %rbx
	cmpq	%rcx, %rax
	je	.L2112
	.p2align 4
	.p2align 3
.L2107:
	movq	8352(%rbx), %rdi
	testq	%rdi, %rdi
	je	.L2110
	movq	8368(%rbx), %rsi
	addq	$8384, %rbx
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	cmpq	32(%rsp), %rbx
	jne	.L2107
.L2112:
	cmpq	$0, 48(%rsp)
	je	.L2072
	movq	32(%rsp), %rsi
	movq	48(%rsp), %rdi
	movl	$32, %edx
	subq	%rdi, %rsi
	call	_ZdlPvmSt11align_val_t@PLT
.L2072:
	movq	72(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L2160
	addq	$88, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
.L2110:
	.cfi_restore_state
	addq	$8384, %rbx
	cmpq	32(%rsp), %rbx
	jne	.L2107
	jmp	.L2112
.L2078:
	movslq	4(%r12), %rsi
	testl	%esi, %esi
	jg	.L2080
	jmp	.L2084
.L2120:
	movq	$0, 32(%rsp)
	movq	$0, 48(%rsp)
	jmp	.L2074
.L2155:
	leaq	.LC11(%rip), %rdi
.LEHB2:
	call	_ZSt20__throw_length_errorPKc@PLT
.L2160:
	call	__stack_chk_fail@PLT
.L2126:
	endbr64
	movq	%rax, %rbp
.L2113:
	movq	48(%rsp), %rbx
	vzeroupper
.L2114:
	cmpq	32(%rsp), %rbx
	je	.L2161
	movq	8352(%rbx), %rdi
	movq	8368(%rbx), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L2115
	call	_ZdlPvm@PLT
.L2115:
	addq	$8384, %rbx
	jmp	.L2114
.L2161:
	movq	48(%rsp), %rax
	movq	%rbx, %rsi
	subq	%rax, %rsi
	testq	%rax, %rax
	je	.L2117
	movl	$32, %edx
	movq	%rax, %rdi
	call	_ZdlPvmSt11align_val_t@PLT
.L2117:
	movq	%rbp, %rdi
	call	_Unwind_Resume@PLT
.LEHE2:
	.cfi_endproc
.LFE6155:
	.globl	__gxx_personality_v0
	.section	.gcc_except_table._ZN11TableSearch3runEd,"aG",@progbits,_ZN11TableSearch3runEd,comdat
.LLSDA6155:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE6155-.LLSDACSB6155
.LLSDACSB6155:
	.uleb128 .LEHB0-.LFB6155
	.uleb128 .LEHE0-.LEHB0
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB1-.LFB6155
	.uleb128 .LEHE1-.LEHB1
	.uleb128 .L2126-.LFB6155
	.uleb128 0
	.uleb128 .LEHB2-.LFB6155
	.uleb128 .LEHE2-.LEHB2
	.uleb128 0
	.uleb128 0
.LLSDACSE6155:
	.section	.text._ZN11TableSearch3runEd,"axG",@progbits,_ZN11TableSearch3runEd,comdat
	.size	_ZN11TableSearch3runEd, .-_ZN11TableSearch3runEd
	.section	.text._ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_,"axG",@progbits,_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_
	.type	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_, @function
_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_:
.LFB7958:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA7958
	endbr64
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	movq	%rdi, %rbp
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	%rsi, %rbx
	subq	$8, %rsp
	.cfi_def_cfa_offset 48
	cmpq	$1, %rsi
	je	.L2187
	movq	%rsi, %rax
	movq	%rdx, %r12
	shrq	$60, %rax
	jne	.L2188
	leaq	0(,%rsi,8), %r13
	movq	%r13, %rdi
.LEHB3:
	call	_Znwm@PLT
	movq	%r13, %rdx
	xorl	%esi, %esi
	movq	%rax, %rdi
	movq	%rax, %r12
	call	memset@PLT
	leaq	48(%rbp), %r10
.L2164:
	movq	16(%rbp), %rsi
	xorl	%r8d, %r8d
	movq	$0, 16(%rbp)
	leaq	16(%rbp), %r9
.L2186:
	testq	%rsi, %rsi
	je	.L2189
.L2167:
	movq	%rsi, %rcx
	xorl	%edx, %edx
	movq	(%rsi), %rsi
	movq	8(%rcx), %rax
	divq	%rbx
	leaq	(%r12,%rdx,8), %rax
	movq	(%rax), %rdi
	testq	%rdi, %rdi
	je	.L2190
	movq	(%rdi), %rdx
	movq	%rdx, (%rcx)
	movq	(%rax), %rax
	movq	%rcx, (%rax)
	testq	%rsi, %rsi
	jne	.L2167
.L2189:
	movq	0(%rbp), %rdi
	movq	8(%rbp), %rsi
	cmpq	%r10, %rdi
	je	.L2168
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L2168:
	movq	%rbx, 8(%rbp)
	movq	%r12, 0(%rbp)
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L2190:
	.cfi_restore_state
	movq	16(%rbp), %rdi
	movq	%rdi, (%rcx)
	movq	%rcx, 16(%rbp)
	movq	%r9, (%rax)
	cmpq	$0, (%rcx)
	je	.L2176
	movq	%rcx, (%r12,%r8,8)
	movq	%rdx, %r8
	jmp	.L2186
	.p2align 4
	.p2align 3
.L2176:
	movq	%rdx, %r8
	jmp	.L2186
	.p2align 4
	.p2align 3
.L2187:
	leaq	48(%rdi), %r12
	movq	$0, 48(%rdi)
	movq	%r12, %r10
	jmp	.L2164
	.p2align 4
	.p2align 3
.L2188:
	shrq	$61, %rbx
	je	.L2166
	call	_ZSt28__throw_bad_array_new_lengthv@PLT
.L2166:
	call	_ZSt17__throw_bad_allocv@PLT
.LEHE3:
.L2177:
	endbr64
	movq	%rax, %rdi
.L2173:
	vzeroupper
	call	__cxa_begin_catch@PLT
	movq	(%r12), %rax
	movq	%rax, 40(%rbp)
.LEHB4:
	call	__cxa_rethrow@PLT
.LEHE4:
.L2178:
	endbr64
	movq	%rax, %rbp
.L2174:
	vzeroupper
	call	__cxa_end_catch@PLT
	movq	%rbp, %rdi
.LEHB5:
	call	_Unwind_Resume@PLT
.LEHE5:
	.cfi_endproc
.LFE7958:
	.section	.gcc_except_table._ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_,"aG",@progbits,_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_,comdat
	.align 4
.LLSDA7958:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATT7958-.LLSDATTD7958
.LLSDATTD7958:
	.byte	0x1
	.uleb128 .LLSDACSE7958-.LLSDACSB7958
.LLSDACSB7958:
	.uleb128 .LEHB3-.LFB7958
	.uleb128 .LEHE3-.LEHB3
	.uleb128 .L2177-.LFB7958
	.uleb128 0x1
	.uleb128 .LEHB4-.LFB7958
	.uleb128 .LEHE4-.LEHB4
	.uleb128 .L2178-.LFB7958
	.uleb128 0
	.uleb128 .LEHB5-.LFB7958
	.uleb128 .LEHE5-.LEHB5
	.uleb128 0
	.uleb128 0
.LLSDACSE7958:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATT7958:
	.section	.text._ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_,"axG",@progbits,_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_,comdat
	.size	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_, .-_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_
	.section	.text._ZN9OptimizerC2Ed,"axG",@progbits,_ZN9OptimizerC5Ed,comdat
	.align 2
	.p2align 4
	.weak	_ZN9OptimizerC2Ed
	.type	_ZN9OptimizerC2Ed, @function
_ZN9OptimizerC2Ed:
.LFB5994:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5994
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	vpxor	%xmm1, %xmm1, %xmm1
	movl	$1, %ecx
	movabsq	$6364136223846793005, %rsi
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	.cfi_offset 15, -24
	.cfi_offset 14, -32
	.cfi_offset 13, -40
	.cfi_offset 12, -48
	.cfi_offset 3, -56
	vmovq	%xmm0, %rbx
	vpxor	%xmm0, %xmm0, %xmm0
	subq	$312, %rsp
	movq	%rdi, %r14
	leaq	24(%rdi), %r13
	movq	%fs:40, %rax
	movq	%rax, 296(%rsp)
	xorl	%eax, %eax
	vmovdqu64	%zmm0, 24(%rdi)
	vmovss	.LC37(%rip), %xmm0
	leaq	72(%rdi), %rax
	vmovdqu	%ymm1, 88(%rdi)
	movq	%rax, 8(%rsp)
	leaq	168(%rdi), %rax
	vmovdqu	%ymm1, 168(%rdi)
	vpxor	%xmm1, %xmm1, %xmm1
	movq	%rax, (%rsp)
	movq	%rax, 120(%rdi)
	leaq	288(%rdi), %rax
	movq	$1, 128(%rdi)
	movq	%rax, 240(%rdi)
	movl	$917413, %eax
	movq	$0, 136(%rdi)
	movq	$0, 144(%rdi)
	movq	$0, 160(%rdi)
	vmovdqu	%xmm1, 208(%rdi)
	movq	$0, 224(%rdi)
	movq	%rax, %rdx
	movq	$1, 248(%rdi)
	movq	$0, 256(%rdi)
	movq	$0, 264(%rdi)
	movq	$0, 280(%rdi)
	movq	$0, 288(%rdi)
	movq	$917413, 296(%rdi)
	vmovss	%xmm0, 152(%rdi)
	vmovss	%xmm0, 272(%rdi)
	.p2align 4
	.p2align 3
.L2192:
	movq	%rdx, %rax
	shrq	$62, %rax
	xorq	%rdx, %rax
	imulq	%rsi, %rax
	leaq	(%rax,%rcx), %rdx
	movq	%rdx, 296(%r14,%rcx,8)
	incq	%rcx
	cmpq	$312, %rcx
	jne	.L2192
	movq	.LC1(%rip), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$312, 2792(%r14)
	movb	$0, 2840(%r14)
	vmovdqu	%xmm0, 2808(%r14)
	vmovdqu	%xmm0, 2824(%r14)
	movq	$0, 2856(%r14)
	movq	%rax, 2848(%r14)
	vzeroupper
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	vmovq	%rbx, %xmm5
	vmulsd	.LC26(%rip), %xmm5, %xmm0
	movq	%rax, 2824(%r14)
	movq	%r14, %rsi
	leaq	_ZSt3cin(%rip), %rdi
	vcvttsd2siq	%xmm0, %rdx
	addq	%rdx, %rax
	movq	%rax, 2832(%r14)
.LEHB6:
	call	_ZNSirsERi@PLT
	movq	%rax, %rdi
	leaq	4(%r14), %rsi
	call	_ZNSirsERi@PLT
	movq	%rax, %rdi
	leaq	8(%r14), %rsi
	call	_ZNSirsERi@PLT
	movq	%rax, %rdi
	leaq	12(%r14), %rsi
	call	_ZNSirsERi@PLT
	movq	%rax, %rdi
	leaq	16(%r14), %rsi
	call	_ZNSirsERi@PLT
	movq	32(%r14), %r12
	movq	24(%r14), %rbx
	movslq	4(%r14), %rsi
	movq	%r12, %rax
	subq	%rbx, %rax
	sarq	$2, %rax
	cmpq	%rax, %rsi
	ja	.L2284
	jnb	.L2283
	leaq	(%rbx,%rsi,4), %rax
	cmpq	%rax, %r12
	je	.L2283
	movq	%rax, %r12
	movq	%rax, 32(%r14)
	cmpq	%rbx, %r12
	je	.L2285
.L2198:
	movq	%rbx, %rsi
	leaq	_ZSt3cin(%rip), %rdi
	call	_ZNSi10_M_extractIjEERSiRT_@PLT
	addq	$4, %rbx
.L2283:
	cmpq	%rbx, %r12
	jne	.L2198
.L2285:
	movq	56(%r14), %rdi
	movq	48(%r14), %rcx
	movabsq	$-3208129404123400281, %rsi
	movslq	16(%r14), %rax
	movq	%rdi, 16(%rsp)
	subq	%rcx, %rdi
	movq	%rdi, %rdx
	sarq	$5, %rdx
	imulq	%rsi, %rdx
	cmpq	%rdx, %rax
	ja	.L2286
	jb	.L2287
.L2200:
	movq	%rcx, 56(%rsp)
	cmpq	%rcx, 16(%rsp)
	je	.L2222
.L2221:
	movq	56(%rsp), %rbx
	leaq	_ZSt3cin(%rip), %rdi
	movq	%rbx, %rsi
	call	_ZNSirsERi@PLT
	movl	(%rbx), %ecx
	testl	%ecx, %ecx
	jle	.L2203
	leaq	84(%rsp), %r12
	xorl	%ebx, %ebx
.L2204:
	movq	%r12, %rsi
	leaq	_ZSt3cin(%rip), %rdi
	call	_ZNSi10_M_extractIjEERSiRT_@PLT
	movl	(%r12), %eax
	movl	(%r14), %edx
	addq	$4, %r12
	movq	56(%rsp), %rsi
	bzhi	%edx, %eax, %ecx
	shrx	%edx, %eax, %eax
	movl	%ecx, 4(%rsi,%rbx,4)
	movl	%eax, 16(%rsi,%rbx,4)
	movl	(%rsi), %ecx
	incq	%rbx
	cmpl	%ebx, %ecx
	jg	.L2204
.L2203:
	leaq	96(%rsp), %rax
	xorl	%esi, %esi
	movl	$192, %edx
	movl	%ecx, 40(%rsp)
	movq	%rax, %rdi
	movq	%rax, 32(%rsp)
	call	memset@PLT
	movq	$0, 48(%rsp)
	movq	$0, 24(%rsp)
	movl	$0, 44(%rsp)
	movl	12(%r14), %eax
	movl	40(%rsp), %ecx
	testl	%eax, %eax
	jle	.L2206
	testl	%ecx, %ecx
	jle	.L2206
.L2210:
	movq	48(%rsp), %rax
	movq	32(%rsp), %rbx
	xorl	%r12d, %r12d
	movq	24(%rsp), %rdi
	movq	%rax, %r15
	subq	%rax, %rbx
	movq	56(%rsp), %rax
	negq	%r15
	leaq	(%rax,%rdi,8), %r13
.L2207:
	movq	%rbx, %rsi
	leaq	_ZSt3cin(%rip), %rdi
	call	_ZNSi10_M_extractIdEERSiRT_@PLT
	movq	48(%rsp), %rax
	incl	%r12d
	addq	$64, %r13
	addq	%rbx, %rax
	addq	$8, %rbx
	vmovsd	(%rax,%r15), %xmm0
	movq	56(%rsp), %rax
	movl	(%rax), %ecx
	vmovsd	%xmm0, -32(%r13)
	cmpl	%r12d, %ecx
	jg	.L2207
	incl	44(%rsp)
	movl	44(%rsp), %eax
	cmpl	12(%r14), %eax
	jge	.L2206
	incq	24(%rsp)
	subq	$24, 48(%rsp)
	testl	%ecx, %ecx
	jg	.L2210
.L2206:
	movl	$1, %eax
	vmovsd	.LC38(%rip), %xmm2
	xorl	%r11d, %r11d
	leaq	288(%rsp), %rsi
	shlx	%ecx, %eax, %eax
	movl	84(%rsp), %r10d
	vmovq	%r14, %xmm6
	movl	%eax, 24(%rsp)
	movq	56(%rsp), %rax
	movl	88(%rsp), %ebx
	leaq	224(%rax), %r12
	movl	92(%rsp), %eax
	movl	%eax, 48(%rsp)
	.p2align 4
	.p2align 3
.L2240:
	movq	32(%rsp), %rax
	movl	%r11d, %edi
	movl	%r11d, %r9d
	movl	%r11d, %r8d
	sarl	%edi
	sarl	$2, %r9d
	movq	%r12, %r15
	andl	$1, %r8d
	andl	$1, %edi
	andl	$1, %r9d
	movl	%r11d, 44(%rsp)
	vmovq	%xmm6, %r13
	.p2align 4
	.p2align 3
.L2220:
	movq	.LC1(%rip), %rdx
	vmovq	%rdx, %xmm0
	testl	%ecx, %ecx
	jle	.L2218
	movl	0(%r13), %edx
	movq	.LC1(%rip), %r11
	shrx	%edx, %r10d, %r14d
	vmovq	%r11, %xmm0
	cmpl	%r14d, %r8d
	je	.L2212
	vfnmadd231sd	(%rax), %xmm2, %xmm0
.L2212:
	cmpl	$1, %ecx
	je	.L2218
	shrx	%edx, %ebx, %r14d
	cmpl	%edi, %r14d
	je	.L2214
	vmovsd	8(%rax), %xmm3
	vfnmadd231sd	.LC38(%rip), %xmm3, %xmm0
.L2214:
	cmpl	$2, %ecx
	je	.L2218
	shrx	%edx, 48(%rsp), %edx
	cmpl	%edx, %r9d
	je	.L2218
	vmovsd	16(%rax), %xmm4
	vfnmadd231sd	.LC38(%rip), %xmm4, %xmm0
.L2218:
	addq	$24, %rax
	vmovsd	%xmm0, (%r15)
	addq	$8, %r15
	cmpq	%rax, %rsi
	jne	.L2220
	movl	44(%rsp), %r11d
	addq	$64, %r12
	incl	%r11d
	cmpl	%r11d, 24(%rsp)
	jne	.L2240
	addq	$736, 56(%rsp)
	vmovq	%xmm6, %r14
	movq	56(%rsp), %rax
	cmpq	%rax, 16(%rsp)
	jne	.L2221
.L2222:
	vmovdqa	.LC40(%rip), %xmm1
	vmovd	(%r14), %xmm0
	leaq	72(%rsp), %r12
	movl	$1, %esi
	movq	8(%rsp), %rdi
	movq	%r12, %rdx
	movl	$-1, 72(%rsp)
	vpminsd	%xmm1, %xmm0, %xmm0
	vmovd	%xmm0, %eax
	vmovd	%xmm0, 2800(%r14)
	shlx	%eax, %esi, %esi
	call	_ZNSt6vectorIjSaIjEE14_M_fill_assignEmRKj
	movl	2800(%r14), %edx
	movq	104(%r14), %rsi
	movl	$1, %eax
	shlx	%edx, %eax, %eax
	movq	96(%r14), %rdx
	movq	%rsi, %rcx
	subq	%rdx, %rcx
	sarq	$6, %rcx
	cmpq	%rcx, %rax
	ja	.L2288
	jb	.L2289
.L2224:
	vmovsd	.LC39(%rip), %xmm1
	movq	144(%r14), %rax
	vxorps	%xmm0, %xmm0, %xmm0
	leaq	152(%r14), %rdi
	vcvtss2sd	152(%r14), %xmm0, %xmm2
	movq	160(%r14), %rbx
	incq	%rax
	vcvtusi2sdq	%rax, %xmm0, %xmm0
	vdivsd	%xmm2, %xmm0, %xmm0
	movq	%rbx, 72(%rsp)
	vdivsd	%xmm2, %xmm1, %xmm1
	vrndscalesd	$10, %xmm0, %xmm0, %xmm0
	vrndscalesd	$10, %xmm1, %xmm1, %xmm1
	vcvttsd2usi	%xmm0, %rax
	vcvttsd2usi	%xmm1, %rsi
	cmpq	%rax, %rsi
	cmovb	%rax, %rsi
	call	_ZNKSt8__detail20_Prime_rehash_policy11_M_next_bktEm@PLT
	movq	%rax, %rsi
	cmpq	128(%r14), %rax
	jne	.L2290
	movq	%rbx, 160(%r14)
.L2191:
	movq	296(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L2291
	addq	$312, %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
.L2289:
	.cfi_restore_state
	salq	$6, %rax
	addq	%rdx, %rax
	cmpq	%rax, %rsi
	je	.L2224
	movq	%rax, 104(%r14)
	jmp	.L2224
.L2287:
	imulq	$736, %rax, %rax
	addq	%rcx, %rax
	cmpq	%rax, 16(%rsp)
	je	.L2200
	movq	%rax, 56(%r14)
	movq	%rax, 16(%rsp)
	jmp	.L2200
.L2288:
	subq	%rcx, %rax
	leaq	96(%r14), %rdi
	movq	%rax, %rsi
	call	_ZNSt6vectorI6ValuesSaIS0_EE17_M_default_appendEm
	jmp	.L2224
.L2286:
	subq	%rdx, %rax
	leaq	48(%r14), %rdi
	movq	%rax, %rsi
	call	_ZNSt6vectorI7ChannelSaIS0_EE17_M_default_appendEm
	movq	56(%r14), %rax
	movq	48(%r14), %rcx
	movq	%rax, 16(%rsp)
	jmp	.L2200
.L2284:
	subq	%rax, %rsi
	movq	%r13, %rdi
	call	_ZNSt6vectorIjSaIjEE17_M_default_appendEm
	movq	32(%r14), %r12
	movq	24(%r14), %rbx
	jmp	.L2283
.L2290:
	leaq	120(%r14), %rdi
	movq	%r12, %rdx
	call	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_
.LEHE6:
	jmp	.L2191
.L2291:
	call	__stack_chk_fail@PLT
.L2246:
	endbr64
	movq	%rax, %r12
.L2228:
	leaq	240(%r14), %rdi
	vzeroupper
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED1Ev
	movq	208(%r14), %rdi
	movq	224(%r14), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L2229
	call	_ZdlPvm@PLT
.L2229:
	movq	176(%r14), %rdi
	movq	192(%r14), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L2230
	call	_ZdlPvm@PLT
.L2230:
	movq	136(%r14), %rdi
.L2231:
	testq	%rdi, %rdi
	je	.L2292
	movq	(%rdi), %rbx
	movl	$32, %esi
	call	_ZdlPvm@PLT
	movq	%rbx, %rdi
	jmp	.L2231
.L2292:
	movq	128(%r14), %rax
	movq	120(%r14), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	128(%r14), %rsi
	movq	$0, 144(%r14)
	movq	$0, 136(%r14)
	movq	120(%r14), %rdi
	cmpq	%rdi, (%rsp)
	jne	.L2293
.L2233:
	movq	96(%r14), %rdi
	movq	112(%r14), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L2234
	movl	$32, %edx
	call	_ZdlPvmSt11align_val_t@PLT
.L2234:
	movq	72(%r14), %rdi
	movq	88(%r14), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L2235
	call	_ZdlPvm@PLT
.L2235:
	movq	48(%r14), %rdi
	movq	64(%r14), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L2236
	movl	$32, %edx
	call	_ZdlPvmSt11align_val_t@PLT
.L2236:
	movq	24(%r14), %rdi
	movq	40(%r14), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L2237
	call	_ZdlPvm@PLT
.L2237:
	movq	%r12, %rdi
.LEHB7:
	call	_Unwind_Resume@PLT
.LEHE7:
.L2293:
	salq	$3, %rsi
	call	_ZdlPvm@PLT
	jmp	.L2233
	.cfi_endproc
.LFE5994:
	.section	.gcc_except_table._ZN9OptimizerC2Ed,"aG",@progbits,_ZN9OptimizerC5Ed,comdat
.LLSDA5994:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE5994-.LLSDACSB5994
.LLSDACSB5994:
	.uleb128 .LEHB6-.LFB5994
	.uleb128 .LEHE6-.LEHB6
	.uleb128 .L2246-.LFB5994
	.uleb128 0
	.uleb128 .LEHB7-.LFB5994
	.uleb128 .LEHE7-.LEHB7
	.uleb128 0
	.uleb128 0
.LLSDACSE5994:
	.section	.text._ZN9OptimizerC2Ed,"axG",@progbits,_ZN9OptimizerC5Ed,comdat
	.size	_ZN9OptimizerC2Ed, .-_ZN9OptimizerC2Ed
	.weak	_ZN9OptimizerC1Ed
	.set	_ZN9OptimizerC1Ed,_ZN9OptimizerC2Ed
	.section	.text.unlikely,"ax",@progbits
	.align 2
.LCOLDB41:
	.text
.LHOTB41:
	.align 2
	.p2align 4
	.type	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0, @function
_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0:
.LFB8915:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA8915
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	movq	%rdx, %r13
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	%rdi, %rbx
	movl	$32, %edi
	movq	%rsi, %r12
	subq	$24, %rsp
	.cfi_def_cfa_offset 64
	movq	%fs:40, %rax
	movq	%rax, 8(%rsp)
	xorl	%eax, %eax
.LEHB8:
	call	_Znwm@PLT
.LEHE8:
	vmovdqu	0(%r13), %xmm0
	xorl	%edx, %edx
	movq	(%r12), %r12
	movq	8(%rbx), %r8
	movq	$0, (%rax)
	movq	%rax, %rbp
	movq	%r12, 8(%rax)
	vmovdqu	%xmm0, 16(%rax)
	movq	%r12, %rax
	divq	%r8
	movq	(%rbx), %rax
	leaq	0(,%rdx,8), %r13
	movq	(%rax,%r13), %rax
	testq	%rax, %rax
	je	.L2295
	movq	(%rax), %rcx
	movq	%rdx, %rdi
	movq	8(%rcx), %rsi
.L2297:
	cmpq	%rsi, %r12
	je	.L2296
	movq	(%rcx), %rcx
	testq	%rcx, %rcx
	je	.L2295
	movq	8(%rcx), %rsi
	xorl	%edx, %edx
	movq	%rsi, %rax
	divq	%r8
	cmpq	%rdx, %rdi
	je	.L2297
.L2295:
	movq	40(%rbx), %rax
	movq	24(%rbx), %rdx
	leaq	32(%rbx), %rdi
	movl	$1, %ecx
	movq	%r8, %rsi
	movq	%rax, (%rsp)
.LEHB9:
	call	_ZNKSt8__detail20_Prime_rehash_policy14_M_need_rehashEmmm@PLT
	movq	%rdx, %rsi
	testb	%al, %al
	jne	.L2318
.L2298:
	movq	(%rbx), %rcx
	addq	%rcx, %r13
	movq	0(%r13), %rax
	testq	%rax, %rax
	je	.L2299
	movq	(%rax), %rax
	movq	%rax, 0(%rbp)
	movq	0(%r13), %rax
	movq	%rbp, (%rax)
.L2300:
	incq	24(%rbx)
	movq	%rbp, %r13
	movl	$1, %r12d
	jmp	.L2303
	.p2align 4
	.p2align 3
.L2296:
	movl	$32, %esi
	movq	%rbp, %rdi
	movq	%rcx, %r13
	xorl	%r12d, %r12d
	call	_ZdlPvm@PLT
.L2303:
	movq	8(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L2319
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	movq	%r13, %rax
	movq	%r12, %rdx
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L2318:
	.cfi_restore_state
	movq	%rsp, %rdx
	movq	%rbx, %rdi
	call	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE9_M_rehashEmRS1_
.LEHE9:
	movq	%r12, %rax
	xorl	%edx, %edx
	divq	8(%rbx)
	leaq	0(,%rdx,8), %r13
	jmp	.L2298
	.p2align 4
	.p2align 3
.L2299:
	movq	16(%rbx), %rax
	movq	%rbp, 16(%rbx)
	movq	%rax, 0(%rbp)
	testq	%rax, %rax
	je	.L2301
	movq	8(%rax), %rax
	xorl	%edx, %edx
	divq	8(%rbx)
	movq	%rbp, (%rcx,%rdx,8)
.L2301:
	leaq	16(%rbx), %rax
	movq	%rax, 0(%r13)
	jmp	.L2300
.L2319:
	call	__stack_chk_fail@PLT
.L2305:
	endbr64
	movq	%rax, %r12
	jmp	.L2302
	.section	.gcc_except_table,"a",@progbits
.LLSDA8915:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE8915-.LLSDACSB8915
.LLSDACSB8915:
	.uleb128 .LEHB8-.LFB8915
	.uleb128 .LEHE8-.LEHB8
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB9-.LFB8915
	.uleb128 .LEHE9-.LEHB9
	.uleb128 .L2305-.LFB8915
	.uleb128 0
.LLSDACSE8915:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC8915
	.type	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0.cold, @function
_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0.cold:
.LFSB8915:
.L2302:
	.cfi_def_cfa_offset 64
	.cfi_offset 3, -40
	.cfi_offset 6, -32
	.cfi_offset 12, -24
	.cfi_offset 13, -16
	movl	$32, %esi
	movq	%rbp, %rdi
	vzeroupper
	call	_ZdlPvm@PLT
	movq	%r12, %rdi
.LEHB10:
	call	_Unwind_Resume@PLT
.LEHE10:
	.cfi_endproc
.LFE8915:
	.section	.gcc_except_table
.LLSDAC8915:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSEC8915-.LLSDACSBC8915
.LLSDACSBC8915:
	.uleb128 .LEHB10-.LCOLDB41
	.uleb128 .LEHE10-.LEHB10
	.uleb128 0
	.uleb128 0
.LLSDACSEC8915:
	.section	.text.unlikely
	.text
	.size	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0, .-_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0
	.section	.text.unlikely
	.size	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0.cold, .-_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0.cold
.LCOLDE41:
	.text
.LHOTE41:
	.section	.text._ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm,"axG",@progbits,_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm
	.type	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm, @function
_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm:
.LFB8076:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA8076
	endbr64
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	movq	%rdi, %rbp
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	%rsi, %rbx
	subq	$8, %rsp
	.cfi_def_cfa_offset 48
	cmpq	$1, %rsi
	je	.L2345
	movq	%rsi, %rax
	movq	%rdx, %r12
	shrq	$60, %rax
	jne	.L2346
	leaq	0(,%rsi,8), %r13
	movq	%r13, %rdi
.LEHB11:
	call	_Znwm@PLT
	movq	%r13, %rdx
	xorl	%esi, %esi
	movq	%rax, %rdi
	movq	%rax, %r12
	call	memset@PLT
	leaq	48(%rbp), %r10
.L2322:
	movq	16(%rbp), %rsi
	xorl	%r8d, %r8d
	movq	$0, 16(%rbp)
	leaq	16(%rbp), %r9
.L2344:
	testq	%rsi, %rsi
	je	.L2347
.L2325:
	movq	%rsi, %rcx
	xorl	%edx, %edx
	movq	(%rsi), %rsi
	movl	8(%rcx), %eax
	divq	%rbx
	leaq	(%r12,%rdx,8), %rax
	movq	(%rax), %rdi
	testq	%rdi, %rdi
	je	.L2348
	movq	(%rdi), %rdx
	movq	%rdx, (%rcx)
	movq	(%rax), %rax
	movq	%rcx, (%rax)
	testq	%rsi, %rsi
	jne	.L2325
.L2347:
	movq	0(%rbp), %rdi
	movq	8(%rbp), %rsi
	cmpq	%r10, %rdi
	je	.L2326
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L2326:
	movq	%rbx, 8(%rbp)
	movq	%r12, 0(%rbp)
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L2348:
	.cfi_restore_state
	movq	16(%rbp), %rdi
	movq	%rdi, (%rcx)
	movq	%rcx, 16(%rbp)
	movq	%r9, (%rax)
	cmpq	$0, (%rcx)
	je	.L2334
	movq	%rcx, (%r12,%r8,8)
	movq	%rdx, %r8
	jmp	.L2344
	.p2align 4
	.p2align 3
.L2334:
	movq	%rdx, %r8
	jmp	.L2344
	.p2align 4
	.p2align 3
.L2345:
	leaq	48(%rdi), %r12
	movq	$0, 48(%rdi)
	movq	%r12, %r10
	jmp	.L2322
	.p2align 4
	.p2align 3
.L2346:
	shrq	$61, %rbx
	je	.L2324
	call	_ZSt28__throw_bad_array_new_lengthv@PLT
.L2324:
	call	_ZSt17__throw_bad_allocv@PLT
.LEHE11:
.L2335:
	endbr64
	movq	%rax, %rdi
.L2331:
	vzeroupper
	call	__cxa_begin_catch@PLT
	movq	(%r12), %rax
	movq	%rax, 40(%rbp)
.LEHB12:
	call	__cxa_rethrow@PLT
.LEHE12:
.L2336:
	endbr64
	movq	%rax, %rbp
.L2332:
	vzeroupper
	call	__cxa_end_catch@PLT
	movq	%rbp, %rdi
.LEHB13:
	call	_Unwind_Resume@PLT
.LEHE13:
	.cfi_endproc
.LFE8076:
	.section	.gcc_except_table
	.align 4
.LLSDA8076:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATT8076-.LLSDATTD8076
.LLSDATTD8076:
	.byte	0x1
	.uleb128 .LLSDACSE8076-.LLSDACSB8076
.LLSDACSB8076:
	.uleb128 .LEHB11-.LFB8076
	.uleb128 .LEHE11-.LEHB11
	.uleb128 .L2335-.LFB8076
	.uleb128 0x1
	.uleb128 .LEHB12-.LFB8076
	.uleb128 .LEHE12-.LEHB12
	.uleb128 .L2336-.LFB8076
	.uleb128 0
	.uleb128 .LEHB13-.LFB8076
	.uleb128 .LEHE13-.LEHB13
	.uleb128 0
	.uleb128 0
.LLSDACSE8076:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATT8076:
	.section	.text._ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm,"axG",@progbits,_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm,comdat
	.size	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm, .-_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm
	.section	.text._ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE21_M_insert_unique_nodeEmmPNS1_10_Hash_nodeIjLb0EEEm,"axG",@progbits,_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE21_M_insert_unique_nodeEmmPNS1_10_Hash_nodeIjLb0EEEm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE21_M_insert_unique_nodeEmmPNS1_10_Hash_nodeIjLb0EEEm
	.type	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE21_M_insert_unique_nodeEmmPNS1_10_Hash_nodeIjLb0EEEm, @function
_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE21_M_insert_unique_nodeEmmPNS1_10_Hash_nodeIjLb0EEEm:
.LFB8109:
	.cfi_startproc
	endbr64
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	movq	%rdx, %r13
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	%rsi, %rbp
	movq	%rdi, %rbx
	movq	%rcx, %r12
	subq	$24, %rsp
	.cfi_def_cfa_offset 64
	movq	24(%rdi), %rdx
	movq	8(%rdi), %rsi
	movq	%r8, %rcx
	movq	%fs:40, %rax
	movq	%rax, 8(%rsp)
	movq	40(%rdi), %rax
	addq	$32, %rdi
	movq	%rax, (%rsp)
	call	_ZNKSt8__detail20_Prime_rehash_policy14_M_need_rehashEmmm@PLT
	testb	%al, %al
	jne	.L2359
	movq	(%rbx), %rsi
	leaq	(%rsi,%rbp,8), %rcx
	movq	(%rcx), %rax
	testq	%rax, %rax
	je	.L2351
.L2361:
	movq	(%rax), %rax
	movq	%rax, (%r12)
	movq	(%rcx), %rax
	movq	%r12, (%rax)
.L2352:
	incq	24(%rbx)
	movq	8(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L2360
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	movq	%r12, %rax
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L2359:
	.cfi_restore_state
	movq	%rdx, %rsi
	movq	%rbx, %rdi
	movq	%rsp, %rdx
	call	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm
	movq	%r13, %rax
	xorl	%edx, %edx
	movq	(%rbx), %rsi
	divq	8(%rbx)
	movq	%rdx, %rbp
	leaq	(%rsi,%rbp,8), %rcx
	movq	(%rcx), %rax
	testq	%rax, %rax
	jne	.L2361
.L2351:
	movq	16(%rbx), %rax
	movq	%rax, (%r12)
	movq	%r12, 16(%rbx)
	movq	(%r12), %rax
	testq	%rax, %rax
	je	.L2353
	movl	8(%rax), %eax
	xorl	%edx, %edx
	divq	8(%rbx)
	movq	%r12, (%rsi,%rdx,8)
.L2353:
	leaq	16(%rbx), %rax
	movq	%rax, (%rcx)
	jmp	.L2352
.L2360:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE8109:
	.size	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE21_M_insert_unique_nodeEmmPNS1_10_Hash_nodeIjLb0EEEm, .-_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE21_M_insert_unique_nodeEmmPNS1_10_Hash_nodeIjLb0EEEm
	.section	.text._ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKjNS1_10_AllocNodeISaINS1_10_Hash_nodeIjLb0EEEEEEEESt4pairINS1_14_Node_iteratorIjLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0,"axG",@progbits,_ZN9Optimizer14informed_seedsEv,comdat
	.align 2
	.p2align 4
	.type	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKjNS1_10_AllocNodeISaINS1_10_Hash_nodeIjLb0EEEEEEEESt4pairINS1_14_Node_iteratorIjLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0, @function
_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKjNS1_10_AllocNodeISaINS1_10_Hash_nodeIjLb0EEEEEEEESt4pairINS1_14_Node_iteratorIjLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0:
.LFB8921:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA8921
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	pushq	%r13
	.cfi_def_cfa_offset 24
	.cfi_offset 13, -24
	pushq	%r12
	.cfi_def_cfa_offset 32
	.cfi_offset 12, -32
	xorl	%edx, %edx
	pushq	%rbp
	.cfi_def_cfa_offset 40
	.cfi_offset 6, -40
	pushq	%rbx
	.cfi_def_cfa_offset 48
	.cfi_offset 3, -48
	movq	%rsi, %rbx
	movq	%rdi, %rbp
	movl	(%rsi), %r13d
	movq	8(%rdi), %rsi
	movq	%r13, %rax
	divq	%rsi
	movq	(%rdi), %rax
	movq	(%rax,%rdx,8), %rax
	movq	%rdx, %r12
	testq	%rax, %rax
	je	.L2363
	movq	(%rax), %r8
	movq	%r13, %rdi
	movl	8(%r8), %ecx
.L2365:
	cmpl	%ecx, %edi
	je	.L2367
	movq	(%r8), %r8
	testq	%r8, %r8
	je	.L2363
	movl	8(%r8), %eax
	xorl	%edx, %edx
	movq	%rax, %rcx
	divq	%rsi
	cmpq	%rdx, %r12
	je	.L2365
.L2363:
	movl	$16, %edi
.LEHB14:
	call	_Znwm@PLT
.LEHE14:
	movl	$1, %r8d
	movq	%r13, %rdx
	movq	%r12, %rsi
	movq	%rax, %r14
	movq	$0, (%rax)
	movl	(%rbx), %eax
	movq	%rbp, %rdi
	movq	%r14, %rcx
	movl	%eax, 8(%r14)
.LEHB15:
	call	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE21_M_insert_unique_nodeEmmPNS1_10_Hash_nodeIjLb0EEEm
.LEHE15:
	movq	%rax, %r8
	xorl	%edx, %edx
	movl	$1, %eax
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	movb	%al, %dl
	popq	%rbp
	.cfi_def_cfa_offset 32
	movq	%r8, %rax
	popq	%r12
	.cfi_def_cfa_offset 24
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L2367:
	.cfi_restore_state
	xorl	%eax, %eax
	xorl	%edx, %edx
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbp
	.cfi_def_cfa_offset 32
	movb	%al, %dl
	popq	%r12
	.cfi_def_cfa_offset 24
	movq	%r8, %rax
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
.L2368:
	.cfi_restore_state
	endbr64
	movq	%rax, %rbp
.L2366:
	movl	$16, %esi
	movq	%r14, %rdi
	vzeroupper
	call	_ZdlPvm@PLT
	movq	%rbp, %rdi
.LEHB16:
	call	_Unwind_Resume@PLT
.LEHE16:
	.cfi_endproc
.LFE8921:
	.section	.gcc_except_table
.LLSDA8921:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE8921-.LLSDACSB8921
.LLSDACSB8921:
	.uleb128 .LEHB14-.LFB8921
	.uleb128 .LEHE14-.LEHB14
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB15-.LFB8921
	.uleb128 .LEHE15-.LEHB15
	.uleb128 .L2368-.LFB8921
	.uleb128 0
	.uleb128 .LEHB16-.LFB8921
	.uleb128 .LEHE16-.LEHB16
	.uleb128 0
	.uleb128 0
.LLSDACSE8921:
	.section	.text._ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKjNS1_10_AllocNodeISaINS1_10_Hash_nodeIjLb0EEEEEEEESt4pairINS1_14_Node_iteratorIjLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0,"axG",@progbits,_ZN9Optimizer14informed_seedsEv,comdat
	.size	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKjNS1_10_AllocNodeISaINS1_10_Hash_nodeIjLb0EEEEEEEESt4pairINS1_14_Node_iteratorIjLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0, .-_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKjNS1_10_AllocNodeISaINS1_10_Hash_nodeIjLb0EEEEEEEESt4pairINS1_14_Node_iteratorIjLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
	.section	.text._ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm,"axG",@progbits,_ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm
	.type	_ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm, @function
_ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm:
.LFB8142:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA8142
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rdi, %rbp
	subq	$8, %rsp
	.cfi_def_cfa_offset 64
	movq	%rsi, %rbx
	cmpq	$1, %rsi
	je	.L2413
	movq	%rsi, %rax
	movq	%rdx, %r12
	shrq	$60, %rax
	jne	.L2414
	leaq	0(,%rsi,8), %r13
	movq	%r13, %rdi
.LEHB17:
	call	_Znwm@PLT
	movq	%r13, %rdx
	xorl	%esi, %esi
	movq	%rax, %rdi
	movq	%rax, %r12
	call	memset@PLT
	leaq	48(%rbp), %rax
	vmovq	%rax, %xmm0
.L2380:
	movq	16(%rbp), %rcx
	movq	$0, 16(%rbp)
	testq	%rcx, %rcx
	je	.L2384
	xorl	%r14d, %r14d
	xorl	%r10d, %r10d
	xorl	%r8d, %r8d
	xorl	%esi, %esi
	leaq	16(%rbp), %r15
	jmp	.L2383
	.p2align 4
	.p2align 3
.L2416:
	movq	(%rsi), %rax
	movl	%edi, %r10d
	movq	%rax, (%rcx)
	movq	%rcx, (%rsi)
.L2386:
	movq	%rcx, %rsi
	testq	%r11, %r11
	je	.L2415
.L2395:
	movq	%r11, %rcx
.L2383:
	movl	8(%rcx), %eax
	xorl	%edx, %edx
	movq	%r8, %r9
	movq	(%rcx), %r11
	divq	%rbx
	testq	%rsi, %rsi
	movq	%rdx, %r13
	movq	%rdx, %r8
	setne	%dl
	cmpq	%r9, %r13
	movl	%edx, %edi
	sete	%al
	andb	%al, %dil
	jne	.L2416
	testb	%r10b, %r10b
	je	.L2387
	movq	(%rsi), %rax
	testq	%rax, %rax
	je	.L2387
	movl	8(%rax), %eax
	xorl	%edx, %edx
	divq	%rbx
	cmpq	%r9, %rdx
	je	.L2387
	movq	%rsi, (%r12,%rdx,8)
.L2387:
	leaq	(%r12,%r13,8), %rax
	movq	(%rax), %rdx
	testq	%rdx, %rdx
	je	.L2417
	movq	(%rdx), %rdx
	xorl	%r10d, %r10d
	movq	%rcx, %rsi
	movq	%rdx, (%rcx)
	movq	(%rax), %rax
	movq	%rcx, (%rax)
	testq	%r11, %r11
	jne	.L2395
.L2415:
	testb	%dil, %dil
	je	.L2384
	movq	(%rcx), %rax
	testq	%rax, %rax
	je	.L2384
	movl	8(%rax), %eax
	xorl	%edx, %edx
	divq	%rbx
	cmpq	%rdx, %r13
	je	.L2384
	movq	%rcx, (%r12,%rdx,8)
.L2384:
	movq	0(%rbp), %rdi
	vmovq	%xmm0, %rax
	movq	8(%rbp), %rsi
	cmpq	%rax, %rdi
	je	.L2390
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L2390:
	movq	%rbx, 8(%rbp)
	movq	%r12, 0(%rbp)
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L2417:
	.cfi_restore_state
	movq	16(%rbp), %rdx
	movq	%rdx, (%rcx)
	movq	%rcx, 16(%rbp)
	movq	%r15, (%rax)
	cmpq	$0, (%rcx)
	je	.L2394
	movq	%rcx, (%r12,%r14,8)
	xorl	%r10d, %r10d
	movq	%r13, %r14
	jmp	.L2386
	.p2align 4
	.p2align 3
.L2394:
	xorl	%r10d, %r10d
	movq	%r13, %r14
	jmp	.L2386
	.p2align 4
	.p2align 3
.L2413:
	leaq	48(%rdi), %r12
	movq	$0, 48(%rdi)
	vmovq	%r12, %xmm0
	jmp	.L2380
	.p2align 4
	.p2align 3
.L2414:
	shrq	$61, %rbx
	je	.L2382
	call	_ZSt28__throw_bad_array_new_lengthv@PLT
.L2382:
	call	_ZSt17__throw_bad_allocv@PLT
.LEHE17:
.L2396:
	endbr64
	movq	%rax, %rdi
.L2391:
	vzeroupper
	call	__cxa_begin_catch@PLT
	movq	(%r12), %rax
	movq	%rax, 40(%rbp)
.LEHB18:
	call	__cxa_rethrow@PLT
.LEHE18:
.L2397:
	endbr64
	movq	%rax, %rbp
.L2392:
	vzeroupper
	call	__cxa_end_catch@PLT
	movq	%rbp, %rdi
.LEHB19:
	call	_Unwind_Resume@PLT
.LEHE19:
	.cfi_endproc
.LFE8142:
	.section	.gcc_except_table
	.align 4
.LLSDA8142:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATT8142-.LLSDATTD8142
.LLSDATTD8142:
	.byte	0x1
	.uleb128 .LLSDACSE8142-.LLSDACSB8142
.LLSDACSB8142:
	.uleb128 .LEHB17-.LFB8142
	.uleb128 .LEHE17-.LEHB17
	.uleb128 .L2396-.LFB8142
	.uleb128 0x1
	.uleb128 .LEHB18-.LFB8142
	.uleb128 .LEHE18-.LEHB18
	.uleb128 .L2397-.LFB8142
	.uleb128 0
	.uleb128 .LEHB19-.LFB8142
	.uleb128 .LEHE19-.LEHB19
	.uleb128 0
	.uleb128 0
.LLSDACSE8142:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATT8142:
	.section	.text._ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm,"axG",@progbits,_ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm,comdat
	.size	_ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm, .-_ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm
	.section	.text._ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm,"axG",@progbits,_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm
	.type	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm, @function
_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm:
.LFB8327:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA8327
	endbr64
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	movq	%rdi, %rbp
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	%rsi, %rbx
	subq	$8, %rsp
	.cfi_def_cfa_offset 48
	cmpq	$1, %rsi
	je	.L2443
	movq	%rsi, %rax
	movq	%rdx, %r12
	shrq	$60, %rax
	jne	.L2444
	leaq	0(,%rsi,8), %r13
	movq	%r13, %rdi
.LEHB20:
	call	_Znwm@PLT
	movq	%r13, %rdx
	xorl	%esi, %esi
	movq	%rax, %rdi
	movq	%rax, %r12
	call	memset@PLT
	leaq	48(%rbp), %r10
.L2420:
	movq	16(%rbp), %rsi
	xorl	%r8d, %r8d
	movq	$0, 16(%rbp)
	leaq	16(%rbp), %r9
.L2442:
	testq	%rsi, %rsi
	je	.L2445
.L2423:
	movq	%rsi, %rcx
	xorl	%edx, %edx
	movq	(%rsi), %rsi
	movq	8(%rcx), %rax
	divq	%rbx
	leaq	(%r12,%rdx,8), %rax
	movq	(%rax), %rdi
	testq	%rdi, %rdi
	je	.L2446
	movq	(%rdi), %rdx
	movq	%rdx, (%rcx)
	movq	(%rax), %rax
	movq	%rcx, (%rax)
	testq	%rsi, %rsi
	jne	.L2423
.L2445:
	movq	0(%rbp), %rdi
	movq	8(%rbp), %rsi
	cmpq	%r10, %rdi
	je	.L2424
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L2424:
	movq	%rbx, 8(%rbp)
	movq	%r12, 0(%rbp)
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L2446:
	.cfi_restore_state
	movq	16(%rbp), %rdi
	movq	%rdi, (%rcx)
	movq	%rcx, 16(%rbp)
	movq	%r9, (%rax)
	cmpq	$0, (%rcx)
	je	.L2432
	movq	%rcx, (%r12,%r8,8)
	movq	%rdx, %r8
	jmp	.L2442
	.p2align 4
	.p2align 3
.L2432:
	movq	%rdx, %r8
	jmp	.L2442
	.p2align 4
	.p2align 3
.L2443:
	leaq	48(%rdi), %r12
	movq	$0, 48(%rdi)
	movq	%r12, %r10
	jmp	.L2420
	.p2align 4
	.p2align 3
.L2444:
	shrq	$61, %rbx
	je	.L2422
	call	_ZSt28__throw_bad_array_new_lengthv@PLT
.L2422:
	call	_ZSt17__throw_bad_allocv@PLT
.LEHE20:
.L2433:
	endbr64
	movq	%rax, %rdi
.L2429:
	vzeroupper
	call	__cxa_begin_catch@PLT
	movq	(%r12), %rax
	movq	%rax, 40(%rbp)
.LEHB21:
	call	__cxa_rethrow@PLT
.LEHE21:
.L2434:
	endbr64
	movq	%rax, %rbp
.L2430:
	vzeroupper
	call	__cxa_end_catch@PLT
	movq	%rbp, %rdi
.LEHB22:
	call	_Unwind_Resume@PLT
.LEHE22:
	.cfi_endproc
.LFE8327:
	.section	.gcc_except_table
	.align 4
.LLSDA8327:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATT8327-.LLSDATTD8327
.LLSDATTD8327:
	.byte	0x1
	.uleb128 .LLSDACSE8327-.LLSDACSB8327
.LLSDACSB8327:
	.uleb128 .LEHB20-.LFB8327
	.uleb128 .LEHE20-.LEHB20
	.uleb128 .L2433-.LFB8327
	.uleb128 0x1
	.uleb128 .LEHB21-.LFB8327
	.uleb128 .LEHE21-.LEHB21
	.uleb128 .L2434-.LFB8327
	.uleb128 0
	.uleb128 .LEHB22-.LFB8327
	.uleb128 .LEHE22-.LEHB22
	.uleb128 0
	.uleb128 0
.LLSDACSE8327:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATT8327:
	.section	.text._ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm,"axG",@progbits,_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm,comdat
	.size	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm, .-_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm
	.section	.text.unlikely
	.align 2
.LCOLDB42:
	.text
.LHOTB42:
	.align 2
	.p2align 4
	.type	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0, @function
_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0:
.LFB8929:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA8929
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	pushq	%r13
	.cfi_def_cfa_offset 24
	.cfi_offset 13, -24
	pushq	%r12
	.cfi_def_cfa_offset 32
	.cfi_offset 12, -32
	movq	%rsi, %r14
	pushq	%rbp
	.cfi_def_cfa_offset 40
	.cfi_offset 6, -40
	pushq	%rbx
	.cfi_def_cfa_offset 48
	.cfi_offset 3, -48
	xorl	%edx, %edx
	movq	%rdi, %rbx
	subq	$16, %rsp
	.cfi_def_cfa_offset 64
	movq	(%rsi), %rbp
	movq	8(%rdi), %rsi
	movq	%fs:40, %rax
	movq	%rax, 8(%rsp)
	xorl	%eax, %eax
	movq	%rbp, %rax
	divq	%rsi
	movq	(%rdi), %rax
	leaq	0(,%rdx,8), %r13
	movq	(%rax,%r13), %rax
	testq	%rax, %rax
	je	.L2448
	movq	(%rax), %r12
	movq	%rdx, %rdi
	movq	8(%r12), %rcx
.L2450:
	cmpq	%rcx, %rbp
	je	.L2457
	movq	(%r12), %r12
	testq	%r12, %r12
	je	.L2448
	movq	8(%r12), %rcx
	xorl	%edx, %edx
	movq	%rcx, %rax
	divq	%rsi
	cmpq	%rdx, %rdi
	je	.L2450
.L2448:
	movl	$16, %edi
.LEHB23:
	call	_Znwm@PLT
.LEHE23:
	movq	24(%rbx), %rdx
	leaq	32(%rbx), %rdi
	movl	$1, %ecx
	movq	%rax, %r12
	movq	$0, (%rax)
	movq	(%r14), %rax
	movq	8(%rbx), %rsi
	movq	%rax, 8(%r12)
	movq	40(%rbx), %rax
	movq	%rax, (%rsp)
.LEHB24:
	call	_ZNKSt8__detail20_Prime_rehash_policy14_M_need_rehashEmmm@PLT
	movq	%rdx, %rsi
	testb	%al, %al
	jne	.L2471
.L2451:
	movq	(%rbx), %rcx
	addq	%rcx, %r13
	movq	0(%r13), %rax
	testq	%rax, %rax
	je	.L2452
	movq	(%rax), %rax
	movq	%rax, (%r12)
	movq	0(%r13), %rax
	movq	%r12, (%rax)
.L2453:
	incq	24(%rbx)
	movl	$1, %eax
	jmp	.L2449
	.p2align 4
	.p2align 3
.L2457:
	xorl	%eax, %eax
.L2449:
	xorl	%edx, %edx
	movb	%al, %dl
	movq	8(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L2472
	addq	$16, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 48
	movq	%r12, %rax
	popq	%rbx
	.cfi_def_cfa_offset 40
	popq	%rbp
	.cfi_def_cfa_offset 32
	popq	%r12
	.cfi_def_cfa_offset 24
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L2471:
	.cfi_restore_state
	movq	%rsp, %rdx
	movq	%rbx, %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm
.LEHE24:
	movq	%rbp, %rax
	xorl	%edx, %edx
	divq	8(%rbx)
	leaq	0(,%rdx,8), %r13
	jmp	.L2451
	.p2align 4
	.p2align 3
.L2452:
	movq	16(%rbx), %rax
	movq	%r12, 16(%rbx)
	movq	%rax, (%r12)
	testq	%rax, %rax
	je	.L2454
	movq	8(%rax), %rax
	xorl	%edx, %edx
	divq	8(%rbx)
	movq	%r12, (%rcx,%rdx,8)
.L2454:
	leaq	16(%rbx), %rax
	movq	%rax, 0(%r13)
	jmp	.L2453
.L2472:
	call	__stack_chk_fail@PLT
.L2458:
	endbr64
	movq	%rax, %rbp
	jmp	.L2455
	.section	.gcc_except_table
.LLSDA8929:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE8929-.LLSDACSB8929
.LLSDACSB8929:
	.uleb128 .LEHB23-.LFB8929
	.uleb128 .LEHE23-.LEHB23
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB24-.LFB8929
	.uleb128 .LEHE24-.LEHB24
	.uleb128 .L2458-.LFB8929
	.uleb128 0
.LLSDACSE8929:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC8929
	.type	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0.cold, @function
_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0.cold:
.LFSB8929:
.L2455:
	.cfi_def_cfa_offset 64
	.cfi_offset 3, -48
	.cfi_offset 6, -40
	.cfi_offset 12, -32
	.cfi_offset 13, -24
	.cfi_offset 14, -16
	movl	$16, %esi
	movq	%r12, %rdi
	vzeroupper
	call	_ZdlPvm@PLT
	movq	%rbp, %rdi
.LEHB25:
	call	_Unwind_Resume@PLT
.LEHE25:
	.cfi_endproc
.LFE8929:
	.section	.gcc_except_table
.LLSDAC8929:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSEC8929-.LLSDACSBC8929
.LLSDACSBC8929:
	.uleb128 .LEHB25-.LCOLDB42
	.uleb128 .LEHE25-.LEHB25
	.uleb128 0
	.uleb128 0
.LLSDACSEC8929:
	.section	.text.unlikely
	.text
	.size	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0, .-_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
	.section	.text.unlikely
	.size	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0.cold, .-_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0.cold
.LCOLDE42:
	.text
.LHOTE42:
	.section	.text._ZN9Optimizer8rememberEmdd,"axG",@progbits,_ZN9Optimizer8rememberEmdd,comdat
	.align 2
	.p2align 4
	.weak	_ZN9Optimizer8rememberEmdd
	.type	_ZN9Optimizer8rememberEmdd, @function
_ZN9Optimizer8rememberEmdd:
.LFB6000:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	vmovsd	%xmm0, %xmm0, %xmm2
	movq	%rdi, %rbx
	subq	$56, %rsp
	.cfi_def_cfa_offset 80
	vmovsd	2848(%rdi), %xmm0
	movq	%rsi, 8(%rsp)
	movq	%fs:40, %rax
	movq	%rax, 40(%rsp)
	xorl	%eax, %eax
	vcomisd	%xmm2, %xmm0
	jbe	.L2474
	vmovsd	%xmm2, 2848(%rdi)
	movq	%rsi, 2856(%rbx)
.L2474:
	movq	208(%rbx), %rdx
	movq	216(%rbx), %rax
	subq	%rdx, %rax
	cmpq	$1520, %rax
	jbe	.L2476
	vmovsd	(%rdx), %xmm0
	vcomisd	%xmm1, %xmm0
	jbe	.L2477
.L2476:
	movq	8(%rsp), %rax
	leaq	16(%rsp), %rsi
	leaq	208(%rbx), %rdi
	vmovsd	%xmm2, (%rsp)
	vmovsd	%xmm1, 16(%rsp)
	movq	%rax, 24(%rsp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	216(%rbx), %r10
	movq	208(%rbx), %rdi
	vmovsd	(%rsp), %xmm2
	movq	%r10, %r8
	vmovsd	-16(%r10), %xmm1
	movq	-8(%r10), %r9
	subq	%rdi, %r8
	movq	%r8, %rdx
	sarq	$4, %rdx
	leaq	-1(%rdx), %rax
	subq	$2, %rdx
	movq	%rdx, %rsi
	shrq	$63, %rsi
	addq	%rdx, %rsi
	sarq	%rsi
	testq	%rax, %rax
	jg	.L2482
	jmp	.L2517
	.p2align 4
	.p2align 3
.L2479:
	cmpq	%r9, 8(%rdx)
	setb	%cl
.L2481:
	salq	$4, %rax
	addq	%rdi, %rax
	testb	%cl, %cl
	je	.L2483
	vmovdqu	(%rdx), %xmm3
	leaq	-1(%rsi), %rcx
	vmovdqu	%xmm3, (%rax)
	movq	%rcx, %rax
	shrq	$63, %rax
	addq	%rax, %rcx
	movq	%rsi, %rax
	sarq	%rcx
	testq	%rsi, %rsi
	jle	.L2518
	movq	%rcx, %rsi
.L2482:
	movq	%rsi, %rdx
	salq	$4, %rdx
	addq	%rdi, %rdx
	vmovsd	(%rdx), %xmm0
	vucomisd	%xmm1, %xmm0
	jp	.L2506
	je	.L2479
.L2506:
	vcomisd	%xmm0, %xmm1
	seta	%cl
	jmp	.L2481
	.p2align 4
	.p2align 3
.L2518:
	movq	%rdx, %rax
.L2483:
	vmovsd	%xmm1, (%rax)
	movq	%r9, 8(%rax)
	cmpq	$1536, %r8
	ja	.L2519
.L2477:
	movq	176(%rbx), %rdx
	movq	184(%rbx), %rax
	subq	%rdx, %rax
	cmpq	$1520, %rax
	jbe	.L2486
	vcomisd	(%rdx), %xmm2
	jnb	.L2473
.L2486:
	movq	8(%rsp), %r8
	movq	248(%rbx), %rdi
	xorl	%edx, %edx
	movq	%r8, %rax
	divq	%rdi
	movq	240(%rbx), %rax
	movq	(%rax,%rdx,8), %rax
	movq	%rdx, %r9
	testq	%rax, %rax
	je	.L2489
	movq	(%rax), %rcx
	movq	8(%rcx), %rsi
.L2491:
	cmpq	%rsi, %r8
	je	.L2473
	movq	(%rcx), %rcx
	testq	%rcx, %rcx
	je	.L2489
	movq	8(%rcx), %rsi
	xorl	%edx, %edx
	movq	%rsi, %rax
	divq	%rdi
	cmpq	%rdx, %r9
	je	.L2491
.L2489:
	leaq	16(%rsp), %rsi
	leaq	176(%rbx), %rdi
	movq	%r8, 24(%rsp)
	vmovsd	%xmm2, 16(%rsp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	184(%rbx), %rax
	movq	176(%rbx), %rdx
	vmovsd	-16(%rax), %xmm1
	movq	-8(%rax), %r8
	subq	%rdx, %rax
	movq	%rax, %rsi
	movq	%rax, %rcx
	sarq	$4, %rsi
	leaq	-1(%rsi), %rax
	subq	$2, %rsi
	movq	%rsi, %rdi
	shrq	$63, %rdi
	addq	%rsi, %rdi
	sarq	%rdi
	testq	%rax, %rax
	jg	.L2496
	jmp	.L2520
	.p2align 4
	.p2align 3
.L2493:
	cmpq	%r8, 8(%rsi)
	setb	%cl
.L2495:
	salq	$4, %rax
	addq	%rdx, %rax
	testb	%cl, %cl
	je	.L2497
	vmovdqu	(%rsi), %xmm4
	leaq	-1(%rdi), %rcx
	vmovdqu	%xmm4, (%rax)
	movq	%rcx, %rax
	shrq	$63, %rax
	addq	%rax, %rcx
	movq	%rdi, %rax
	sarq	%rcx
	testq	%rdi, %rdi
	jle	.L2521
	movq	%rcx, %rdi
.L2496:
	movq	%rdi, %rsi
	salq	$4, %rsi
	addq	%rdx, %rsi
	vmovsd	(%rsi), %xmm0
	vucomisd	%xmm1, %xmm0
	jp	.L2507
	je	.L2493
.L2507:
	vcomisd	%xmm0, %xmm1
	seta	%cl
	jmp	.L2495
	.p2align 4
	.p2align 3
.L2521:
	movq	%rsi, %rax
.L2497:
	leaq	240(%rbx), %rbp
	vmovsd	%xmm1, (%rax)
	movq	%r8, 8(%rax)
	leaq	8(%rsp), %rsi
	movq	%rbp, %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
	movq	176(%rbx), %rdx
	movq	184(%rbx), %rax
	subq	%rdx, %rax
	cmpq	$1536, %rax
	ja	.L2522
	.p2align 4
	.p2align 3
.L2473:
	movq	40(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L2523
	addq	$56, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L2519:
	.cfi_restore_state
	leaq	-16(%r10), %rbp
	cmpq	$16, %r8
	jg	.L2524
.L2485:
	movq	%rbp, 216(%rbx)
	jmp	.L2477
	.p2align 4
	.p2align 3
.L2524:
	vmovdqu	(%rdi), %xmm5
	movq	-16(%r10), %rax
	movq	%rbp, %rdx
	xorl	%esi, %esi
	movq	-8(%r10), %rcx
	subq	%rdi, %rdx
	vmovsd	%xmm2, (%rsp)
	sarq	$4, %rdx
	vmovq	%rax, %xmm0
	vmovdqu	%xmm5, -16(%r10)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	vmovsd	(%rsp), %xmm2
	jmp	.L2485
.L2522:
	movq	8(%rdx), %rsi
	movq	%rbp, %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE8_M_eraseESt17integral_constantIbLb1EERKm.isra.0
	movq	184(%rbx), %rax
	movq	176(%rbx), %rdi
	movq	%rax, %rdx
	leaq	-16(%rax), %rbp
	subq	%rdi, %rdx
	cmpq	$16, %rdx
	jg	.L2498
.L2499:
	movq	%rbp, 184(%rbx)
	jmp	.L2473
.L2517:
	leaq	-16(%rdi,%r8), %rax
	jmp	.L2483
.L2498:
	vmovdqu	(%rdi), %xmm6
	movq	-16(%rax), %rdx
	xorl	%esi, %esi
	movq	-8(%rax), %rcx
	vmovq	%rdx, %xmm0
	movq	%rbp, %rdx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm6, -16(%rax)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	jmp	.L2499
.L2520:
	leaq	-16(%rdx,%rcx), %rax
	jmp	.L2497
.L2523:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE6000:
	.size	_ZN9Optimizer8rememberEmdd, .-_ZN9Optimizer8rememberEmdd
	.text
	.align 2
	.p2align 4
	.type	_ZN9Optimizer8evaluateEmb.constprop.0, @function
_ZN9Optimizer8evaluateEmb.constprop.0:
.LFB8934:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	andq	$-64, %rsp
	subq	$4096, %rsp
	orq	$0, (%rsp)
	subq	$4096, %rsp
	orq	$0, (%rsp)
	subq	$1472, %rsp
	.cfi_offset 15, -24
	.cfi_offset 14, -32
	.cfi_offset 13, -40
	.cfi_offset 12, -48
	.cfi_offset 3, -56
	xorl	%edx, %edx
	movq	%rdi, 112(%rsp)
	movq	%rdi, %rcx
	movq	128(%rdi), %rdi
	movq	%rsi, 152(%rsp)
	movq	%rsi, %rbx
	movq	%fs:40, %rax
	movq	%rax, 9656(%rsp)
	xorl	%eax, %eax
	movq	%rsi, %rax
	divq	%rdi
	movq	120(%rcx), %rax
	movq	(%rax,%rdx,8), %rax
	testq	%rax, %rax
	je	.L2526
	movq	(%rax), %rcx
	movq	%rdx, %r8
	movq	8(%rcx), %rsi
.L2528:
	cmpq	%rsi, %rbx
	je	.L2527
	movq	(%rcx), %rcx
	testq	%rcx, %rcx
	je	.L2526
	movq	8(%rcx), %rsi
	xorl	%edx, %edx
	movq	%rsi, %rax
	divq	%rdi
	cmpq	%rdx, %r8
	je	.L2528
.L2526:
	movq	112(%rsp), %rcx
	movq	2808(%rcx), %rax
	movq	%rax, 144(%rsp)
	incq	%rax
	movq	%rax, 2808(%rcx)
	testb	%al, %al
	je	.L2808
.L2530:
	leaq	896(%rsp), %rax
	xorl	%esi, %esi
	movl	$512, %edx
	movq	%rax, %rdi
	movq	%rax, 80(%rsp)
	call	memset@PLT
	testq	%rbx, %rbx
	vxorps	%xmm7, %xmm7, %xmm7
	je	.L2658
	movq	112(%rsp), %rax
	movl	$1, %edi
	leaq	900(%rsp), %r9
	movq	24(%rax), %r10
	jmp	.L2539
.L2810:
	vpbroadcastd	%edx, %zmm0
	vpxord	896(%rsp), %zmm0, %zmm1
	movq	80(%rsp), %rax
	movl	%edi, %esi
	movslq	%edi, %rcx
	shrl	$4, %esi
	leaq	(%rax,%rcx,4), %rax
	vmovdqu32	%zmm1, (%rax)
	cmpl	$1, %esi
	je	.L2533
	vpxord	960(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 64(%rax)
	cmpl	$2, %esi
	je	.L2533
	vpxord	1024(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 128(%rax)
	cmpl	$3, %esi
	je	.L2533
	vpxord	1088(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 192(%rax)
	cmpl	$4, %esi
	je	.L2533
	vpxord	1152(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 256(%rax)
	cmpl	$5, %esi
	je	.L2533
	vpxord	1216(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 320(%rax)
	cmpl	$6, %esi
	je	.L2533
	vpxord	1280(%rsp), %zmm0, %zmm0
	vmovdqu32	%zmm0, 384(%rax)
.L2533:
	movl	%edi, %eax
	andl	$-16, %eax
	testb	$15, %dil
	je	.L2538
	movl	%edi, %esi
	subl	%eax, %esi
	leal	-1(%rsi), %r8d
	cmpl	$6, %r8d
	jbe	.L2535
	movl	%eax, %r8d
	vpbroadcastd	%edx, %ymm0
	vpxor	896(%rsp,%r8,4), %ymm0, %ymm0
	addq	%r8, %rcx
	vmovdqu	%ymm0, 896(%rsp,%rcx,4)
	movl	%esi, %ecx
	andl	$-8, %ecx
	addl	%ecx, %eax
	cmpl	%ecx, %esi
	je	.L2538
.L2535:
	movslq	%eax, %rsi
	leal	(%rdi,%rax), %ecx
	movl	896(%rsp,%rsi,4), %r11d
	movslq	%ecx, %rcx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rcx,4)
	leal	1(%rax), %ecx
	cmpl	%ecx, %edi
	jle	.L2538
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	leal	2(%rax), %ecx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%ecx, %edi
	jle	.L2538
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	leal	3(%rax), %ecx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%ecx, %edi
	jle	.L2538
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	leal	4(%rax), %ecx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%ecx, %edi
	jle	.L2538
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	leal	5(%rax), %ecx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%ecx, %edi
	jle	.L2538
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	addl	$6, %eax
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%eax, %edi
	jle	.L2538
	leal	(%rdi,%rax), %ecx
	cltq
	xorl	896(%rsp,%rax,4), %edx
	movslq	%ecx, %rcx
	movl	%edx, 896(%rsp,%rcx,4)
.L2538:
	addl	%edi, %edi
	blsr	%rbx, %rbx
	je	.L2809
.L2539:
	tzcntq	%rbx, %rax
	leal	-1(%rdi), %ecx
	movl	(%r10,%rax,4), %edx
	cmpl	$14, %ecx
	ja	.L2810
	movq	80(%rsp), %rax
	leaq	(%r9,%rcx,4), %r8
	movslq	%edi, %rcx
.L2537:
	movl	(%rax), %esi
	xorl	%edx, %esi
	movl	%esi, (%rax,%rcx,4)
	addq	$4, %rax
	cmpq	%r8, %rax
	jne	.L2537
	addl	%edi, %edi
	blsr	%rbx, %rbx
	jne	.L2539
.L2809:
	vmovsd	.LC1(%rip), %xmm6
	vcvtsi2sdl	%edi, %xmm7, %xmm3
	movslq	%edi, %rax
	salq	$2, %rax
	movq	%rax, 40(%rsp)
	vdivsd	%xmm3, %xmm6, %xmm3
	vmovsd	%xmm6, 72(%rsp)
.L2531:
	movq	112(%rsp), %r8
	leal	-1(%rdi), %r13d
	leaq	1408(%rsp), %rbx
	movl	$32, %r15d
	movq	80(%rsp), %r11
	movq	%r13, %rax
	movq	%rbx, 120(%rsp)
	salq	$6, %rax
	leaq	1472(%rsp,%rax), %r14
	vmovq	72(%r8), %xmm2
	vmovq	96(%r8), %xmm1
.L2547:
	movl	(%r11), %r10d
	movl	2800(%r8), %eax
	movl	%r10d, %r12d
	cmpl	%eax, (%r8)
	jle	.L2540
	imull	$-1640531535, %r10d, %r12d
	movl	%r15d, %edx
	subl	%eax, %edx
	shrx	%edx, %r12d, %r12d
.L2540:
	vmovq	%xmm2, %rax
	vmovq	%xmm1, %rcx
	leaq	(%rax,%r12,4), %rax
	salq	$6, %r12
	addq	%rcx, %r12
	cmpl	(%rax), %r10d
	je	.L2541
	movq	48(%r8), %rdx
	movq	56(%r8), %rsi
	incq	2816(%r8)
	vbroadcastsd	.LC1(%rip), %zmm0
	movl	%r10d, (%rax)
	cmpq	%rsi, %rdx
	je	.L2542
.L2543:
	movl	(%rdx), %r9d
	xorl	%eax, %eax
	testl	%r9d, %r9d
	jle	.L2546
	movl	4(%rdx), %eax
	andl	%r10d, %eax
	popcntl	%eax, %eax
	andl	$1, %eax
	cmpl	$1, %r9d
	je	.L2546
	movl	8(%rdx), %ecx
	andl	%r10d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	addl	%ecx, %ecx
	orl	%ecx, %eax
	cmpl	$2, %r9d
	je	.L2546
	movl	12(%rdx), %ecx
	andl	%r10d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	sall	$2, %ecx
	orl	%ecx, %eax
.L2546:
	cltq
	addq	$736, %rdx
	salq	$6, %rax
	vmulpd	-512(%rdx,%rax), %zmm0, %zmm0
	cmpq	%rdx, %rsi
	jne	.L2543
.L2542:
	vmovupd	%zmm0, (%r12)
.L2541:
	vmovdqa	(%r12), %xmm4
	addq	$64, %rbx
	addq	$4, %r11
	vmovdqa	48(%r12), %xmm5
	vmovdqa	%xmm4, -64(%rbx)
	vmovdqa	16(%r12), %xmm4
	vmovdqa	%xmm5, -16(%rbx)
	vmovdqa	%xmm4, -48(%rbx)
	vmovdqa	32(%r12), %xmm4
	vmovdqa	%xmm4, -32(%rbx)
	cmpq	%rbx, %r14
	jne	.L2547
	movl	$1, %r9d
	cmpl	$1, %edi
	je	.L2549
.L2548:
	movq	120(%rsp), %rdx
	movslq	%r9d, %rsi
	xorl	%r8d, %r8d
	addl	%r9d, %r9d
	salq	$6, %rsi
	.p2align 4
	.p2align 3
.L2552:
	leaq	(%rdx,%rsi), %rcx
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L2550:
	vmovapd	(%rdx,%rax), %zmm0
	vmovapd	(%rcx,%rax), %zmm1
	vaddpd	%zmm1, %zmm0, %zmm2
	vsubpd	%zmm1, %zmm0, %zmm0
	vmovapd	%zmm2, (%rdx,%rax)
	vmovapd	%zmm0, (%rcx,%rax)
	addq	$64, %rax
	cmpq	%rsi, %rax
	jne	.L2550
	addl	%r9d, %r8d
	leaq	(%rax,%rcx), %rdx
	cmpl	%edi, %r8d
	jl	.L2552
	cmpl	%edi, %r9d
	jl	.L2548
.L2549:
	movq	120(%rsp), %rax
	vbroadcastsd	%xmm3, %zmm3
.L2553:
	vmulpd	(%rax), %zmm3, %zmm0
	addq	$64, %rax
	vmovapd	%zmm0, -64(%rax)
	cmpq	%rax, %r14
	jne	.L2553
	movq	112(%rsp), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqa	%xmm0, 192(%rsp)
	vmovdqa	%xmm0, 208(%rsp)
	vmovdqa	%xmm0, 224(%rsp)
	vmovdqa	%xmm0, 240(%rsp)
	movl	12(%rax), %r15d
	testl	%r15d, %r15d
	jle	.L2811
	vmovsd	72(%rsp), %xmm4
	leal	-1(%r15), %eax
	vcvtsi2sdl	%r15d, %xmm7, %xmm0
	movl	%eax, 100(%rsp)
	vdivsd	%xmm0, %xmm4, %xmm0
	cmpl	$6, %eax
	jbe	.L2662
	movl	%r15d, %edx
	vbroadcastsd	%xmm0, %zmm1
	andl	$-8, %edx
	vmovapd	%zmm1, 192(%rsp)
	movl	%edx, %eax
	cmpl	%r15d, %edx
	je	.L2558
.L2556:
	movl	%r15d, %ecx
	subl	%edx, %ecx
	leal	-1(%rcx), %esi
	cmpl	$2, %esi
	jbe	.L2559
	vbroadcastsd	%xmm0, %ymm1
	vmovapd	%ymm1, 192(%rsp,%rdx,8)
	movl	%ecx, %edx
	andl	$-4, %edx
	addl	%edx, %eax
	cmpl	%ecx, %edx
	je	.L2558
.L2559:
	movslq	%eax, %rdx
	vmovsd	%xmm0, 192(%rsp,%rdx,8)
	leal	1(%rax), %edx
	cmpl	%edx, %r15d
	jle	.L2558
	movslq	%edx, %rdx
	addl	$2, %eax
	vmovsd	%xmm0, 192(%rsp,%rdx,8)
	cmpl	%eax, %r15d
	jle	.L2558
	cltq
	vmovsd	%xmm0, 192(%rsp,%rax,8)
.L2558:
	xorl	%eax, %eax
	testl	%r15d, %r15d
	vmovsd	72(%rsp), %xmm5
	leaq	256(%rsp), %rbx
	setle	%al
	vmovsd	.LC3(%rip), %xmm9
	movl	$2, 64(%rsp)
	vxorpd	%xmm8, %xmm8, %xmm8
	leal	-1(%rax,%rax), %eax
	movl	%eax, 36(%rsp)
	movslq	%r15d, %rax
	salq	$3, %rax
	movq	%rax, 24(%rsp)
	leaq	256(%rsp,%rax), %rax
	movq	%rax, 56(%rsp)
	movl	%r15d, %eax
	andl	$-8, %eax
	testl	%r15d, %r15d
	movl	%eax, 68(%rsp)
	leaq	384(%rsp), %rax
	vmovsd	%xmm5, 48(%rsp)
	vmovsd	%xmm5, 88(%rsp)
	movq	%rax, 104(%rsp)
	leaq	388(%rsp,%r13,4), %rax
	movq	%rax, 8(%rsp)
	movl	$1, %eax
	vmovsd	.LC47(%rip), %xmm5
	cmovg	%r15d, %eax
	movl	%eax, 20(%rsp)
	andl	$-8, %eax
	testl	%r15d, %r15d
	movl	%eax, 32(%rsp)
	movl	100(%rsp), %eax
	leaq	8(,%rax,8), %r13
	movl	$8, %eax
	cmovg	%r13, %rax
	movq	%rax, 128(%rsp)
.L2555:
	testl	%r15d, %r15d
	jle	.L2619
	cmpl	$6, 100(%rsp)
	jbe	.L2663
	vmovapd	.LC45(%rip), %zmm4
	movl	68(%rsp), %eax
	movl	%eax, %edx
	vmovapd	%zmm4, 256(%rsp)
	cmpl	%r15d, %eax
	je	.L2619
.L2561:
	movl	%r15d, %ecx
	subl	%edx, %ecx
	leal	-1(%rcx), %esi
	cmpl	$2, %esi
	jbe	.L2563
	vmovapd	.LC46(%rip), %ymm4
	vmovapd	%ymm4, 256(%rsp,%rdx,8)
	movl	%ecx, %edx
	andl	$-4, %edx
	addl	%edx, %eax
	cmpl	%ecx, %edx
	je	.L2619
.L2563:
	movq	.LC43(%rip), %rcx
	movslq	%eax, %rdx
	movq	%rcx, 256(%rsp,%rdx,8)
	leal	1(%rax), %edx
	cmpl	%r15d, %edx
	jge	.L2619
	movslq	%edx, %rdx
	addl	$2, %eax
	movq	%rcx, 256(%rsp,%rdx,8)
	cmpl	%eax, %r15d
	jle	.L2619
	cltq
	movq	%rcx, 256(%rsp,%rax,8)
.L2619:
	movq	120(%rsp), %rdi
	xorl	%r9d, %r9d
	movq	%r14, 144(%rsp)
	movq	104(%rsp), %rdx
	movq	%r9, %r14
	movl	36(%rsp), %r12d
	movl	68(%rsp), %esi
	movl	32(%rsp), %r8d
	movl	20(%rsp), %r10d
	movq	8(%rsp), %r11
	movq	%rdi, %r9
	jmp	.L2565
.L2656:
	movq	.LC43(%rip), %rax
	movl	$1, (%rdx)
	vmovq	%rax, %xmm0
	cmpl	$7, %r15d
	jle	.L2665
.L2814:
	vmovapd	256(%rsp), %zmm6
	vbroadcastsd	%xmm0, %zmm1
	vfnmadd132pd	(%r9), %zmm6, %zmm1
	vmovapd	%zmm1, 256(%rsp)
	cmpl	%r10d, %r8d
	je	.L2573
	movl	%r8d, %eax
	movl	%r8d, %ecx
.L2571:
	movl	%r10d, %edi
	subl	%eax, %edi
	leal	-1(%rdi), %r13d
	cmpl	$2, %r13d
	jbe	.L2574
	salq	$3, %rax
	vbroadcastsd	%xmm0, %ymm1
	leaq	(%rbx,%rax), %r13
	vmovapd	0(%r13), %ymm6
	vfnmadd132pd	(%r9,%rax), %ymm6, %ymm1
	movl	%edi, %eax
	andl	$-4, %eax
	addl	%eax, %ecx
	vmovapd	%ymm1, 0(%r13)
	cmpl	%edi, %eax
	je	.L2573
.L2574:
	movslq	%ecx, %rax
	leaq	(%r9,%rax,8), %rdi
	vmovsd	(%rdi), %xmm1
	vfnmadd213sd	256(%rsp,%rax,8), %xmm0, %xmm1
	vmovsd	%xmm1, 256(%rsp,%rax,8)
	leal	1(%rcx), %eax
	cmpl	%eax, %r15d
	jle	.L2573
	cltq
	vmovsd	8(%rdi), %xmm1
	addl	$2, %ecx
	vfnmadd213sd	256(%rsp,%rax,8), %xmm0, %xmm1
	vmovsd	%xmm1, 256(%rsp,%rax,8)
	cmpl	%ecx, %r15d
	jle	.L2573
	movslq	%ecx, %rcx
	vmovsd	256(%rsp,%rcx,8), %xmm6
	vfnmadd132sd	16(%rdi), %xmm6, %xmm0
	vmovsd	%xmm0, 256(%rsp,%rcx,8)
.L2573:
	addq	$4, %rdx
	addq	$64, %r9
	addq	$8, %r14
	cmpq	%r11, %rdx
	je	.L2812
.L2565:
	testl	%r15d, %r15d
	jle	.L2813
	cmpl	$6, 100(%rsp)
	jbe	.L2664
	vmovapd	(%r9), %zmm4
	vmulpd	192(%rsp), %zmm4, %zmm1
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vextractf64x2	$0x1, %ymm1, %xmm0
	vaddsd	%xmm8, %xmm1, %xmm3
	vextractf64x4	$0x1, %zmm1, %ymm1
	vaddsd	%xmm3, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm0, %xmm2
	vunpckhpd	%xmm0, %xmm0, %xmm0
	vaddsd	%xmm2, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vaddsd	%xmm0, %xmm1, %xmm0
	vextractf64x2	$0x1, %ymm1, %xmm1
	vaddsd	%xmm0, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm1, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm1, %xmm0, %xmm0
	cmpl	%r15d, %esi
	je	.L2567
	movl	%esi, %edi
	movl	%esi, %eax
.L2566:
	movl	%r15d, %ecx
	subl	%edi, %ecx
	leal	-1(%rcx), %r13d
	cmpl	$2, %r13d
	jbe	.L2568
	leaq	(%rdi,%r14), %r13
	vmovapd	1408(%rsp,%r13,8), %ymm1
	vmulpd	192(%rsp,%rdi,8), %ymm1, %ymm1
	movl	%ecx, %edi
	andl	$-4, %edi
	addl	%edi, %eax
	vaddsd	%xmm0, %xmm1, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vextractf64x2	$0x1, %ymm1, %xmm1
	vaddsd	%xmm0, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm1, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm1, %xmm0, %xmm0
	cmpl	%ecx, %edi
	je	.L2567
.L2568:
	movslq	%eax, %rcx
	vmovsd	192(%rsp,%rcx,8), %xmm4
	leaq	(%r9,%rcx,8), %rdi
	leal	1(%rax), %ecx
	vfmadd231sd	(%rdi), %xmm4, %xmm0
	cmpl	%ecx, %r15d
	jle	.L2567
	movslq	%ecx, %rcx
	addl	$2, %eax
	vmovsd	192(%rsp,%rcx,8), %xmm6
	vfmadd231sd	8(%rdi), %xmm6, %xmm0
	cmpl	%eax, %r15d
	jle	.L2567
	vmovsd	16(%rdi), %xmm4
	cltq
	vfmadd231sd	192(%rsp,%rax,8), %xmm4, %xmm0
.L2567:
	vcomisd	%xmm8, %xmm0
	jnb	.L2656
	vcvtsi2sdl	%r12d, %xmm7, %xmm0
	movl	%r12d, (%rdx)
	vmulsd	.LC43(%rip), %xmm0, %xmm0
	cmpl	$7, %r15d
	jg	.L2814
.L2665:
	xorl	%eax, %eax
	xorl	%ecx, %ecx
	jmp	.L2571
.L2527:
	vmovsd	16(%rcx), %xmm7
	vmovsd	%xmm7, 88(%rsp)
.L2525:
	movq	9656(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L2815
	vmovsd	88(%rsp), %xmm0
	leaq	-40(%rbp), %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
.L2812:
	.cfi_restore_state
	movq	56(%rsp), %rdx
	vmovsd	256(%rsp), %xmm10
	movq	144(%rsp), %r14
	cmpq	%rbx, %rdx
	je	.L2666
	leaq	264(%rsp), %rax
	vmovsd	%xmm10, %xmm10, %xmm4
	cmpq	%rax, %rdx
	je	.L2578
	.p2align 4
	.p2align 3
.L2580:
	vmovsd	(%rax), %xmm0
	addq	$8, %rax
	vmaxsd	%xmm4, %xmm0, %xmm4
	cmpq	%rax, %rdx
	jne	.L2580
.L2578:
	testl	%r15d, %r15d
	jle	.L2669
.L2821:
	vaddsd	%xmm8, %xmm10, %xmm10
	cmpl	$1, %r15d
	je	.L2581
	vaddsd	264(%rsp), %xmm10, %xmm10
	cmpl	$2, %r15d
	je	.L2581
	vaddsd	272(%rsp), %xmm10, %xmm10
	cmpl	$3, %r15d
	je	.L2581
	vaddsd	280(%rsp), %xmm10, %xmm10
	cmpl	$4, %r15d
	je	.L2581
	vaddsd	288(%rsp), %xmm10, %xmm10
	cmpl	$5, %r15d
	je	.L2581
	vaddsd	296(%rsp), %xmm10, %xmm10
	cmpl	$6, %r15d
	je	.L2581
	vaddsd	304(%rsp), %xmm10, %xmm10
	cmpl	$7, %r15d
	je	.L2581
	vaddsd	312(%rsp), %xmm10, %xmm10
.L2581:
	movq	%rbx, %rdi
	movl	$3, 96(%rsp)
	movl	%r15d, %ebx
	.p2align 4
	.p2align 3
.L2583:
	movq	120(%rsp), %r15
	xorl	%eax, %eax
	movq	%r14, %r12
	movq	104(%rsp), %r13
	jmp	.L2599
	.p2align 4
	.p2align 3
.L2653:
	vsubsd	%xmm4, %xmm1, %xmm2
	vandpd	.LC5(%rip), %xmm2, %xmm2
	vcomisd	%xmm2, %xmm5
	jbe	.L2596
	vsubsd	%xmm5, %xmm10, %xmm2
	vcomisd	%xmm0, %xmm2
	ja	.L2816
.L2596:
	addq	$64, %r15
	addq	$4, %r13
	cmpq	%r15, %r12
	je	.L2817
.L2599:
	vsubsd	%xmm5, %xmm4, %xmm6
	testl	%ebx, %ebx
	jle	.L2584
	movl	0(%r13), %r14d
	vmovsd	(%r15), %xmm0
	vcvtsi2sdl	%r14d, %xmm7, %xmm2
	vfmadd213sd	256(%rsp), %xmm2, %xmm0
	vmaxsd	%xmm9, %xmm0, %xmm1
	vmovsd	%xmm0, 320(%rsp)
	vaddsd	%xmm8, %xmm0, %xmm0
	cmpl	$1, %ebx
	je	.L2586
	vmovsd	8(%r15), %xmm3
	vfmadd213sd	264(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 328(%rsp)
	cmpl	$2, %ebx
	je	.L2586
	vmovsd	16(%r15), %xmm3
	vfmadd213sd	272(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 336(%rsp)
	cmpl	$3, %ebx
	je	.L2586
	vmovsd	24(%r15), %xmm3
	vfmadd213sd	280(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 344(%rsp)
	cmpl	$4, %ebx
	je	.L2586
	vmovsd	32(%r15), %xmm3
	vfmadd213sd	288(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 352(%rsp)
	cmpl	$5, %ebx
	je	.L2586
	vmovsd	40(%r15), %xmm3
	vfmadd213sd	296(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 360(%rsp)
	cmpl	$6, %ebx
	je	.L2586
	vmovsd	48(%r15), %xmm3
	vfmadd213sd	304(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 368(%rsp)
	cmpl	$7, %ebx
	je	.L2586
	vmovsd	312(%rsp), %xmm3
	vfmadd132sd	56(%r15), %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm2, %xmm1
	vaddsd	%xmm2, %xmm0, %xmm0
	vmovsd	%xmm2, 376(%rsp)
.L2586:
	vcomisd	%xmm1, %xmm6
	jbe	.L2653
.L2594:
	movq	128(%rsp), %rdx
	leaq	320(%rsp), %rsi
	vmovsd	%xmm1, 136(%rsp)
	vmovsd	%xmm0, 144(%rsp)
	vzeroupper
	call	memcpy@PLT
	vmovsd	136(%rsp), %xmm1
	vxorps	%xmm7, %xmm7, %xmm7
	vmovsd	144(%rsp), %xmm0
	movq	%rax, %rdi
	movq	.LC47(%rip), %rax
	vxorpd	%xmm8, %xmm8, %xmm8
	vmovq	%rax, %xmm5
	movq	.LC3(%rip), %rax
	vmovsd	%xmm1, %xmm1, %xmm4
	vmovsd	%xmm0, %xmm0, %xmm10
	vmovq	%rax, %xmm9
.L2595:
	negl	%r14d
	addq	$64, %r15
	movl	$1, %eax
	addq	$4, %r13
	movl	%r14d, -4(%r13)
	cmpq	%r15, %r12
	jne	.L2599
.L2817:
	movq	%r12, %r14
	testb	%al, %al
	je	.L2600
	decl	96(%rsp)
	jne	.L2583
.L2600:
	vmovsd	88(%rsp), %xmm6
	movl	%ebx, %r15d
	movq	%rdi, %rbx
	vcomisd	%xmm4, %xmm6
	jbe	.L2818
.L2601:
	movq	40(%rsp), %rdx
	movq	104(%rsp), %rsi
	vmovsd	%xmm10, 136(%rsp)
	vmovsd	%xmm4, 144(%rsp)
	movq	80(%rsp), %rdi
	vzeroupper
	call	memcpy@PLT
	movq	.LC3(%rip), %rax
	vxorpd	%xmm8, %xmm8, %xmm8
	vmovsd	136(%rsp), %xmm10
	vmovsd	144(%rsp), %xmm4
	vxorps	%xmm7, %xmm7, %xmm7
	vmovq	%rax, %xmm9
	movq	.LC47(%rip), %rax
	vmovq	%rax, %xmm5
	vmovsd	%xmm10, 48(%rsp)
	vmovsd	%xmm4, 88(%rsp)
.L2602:
	movq	56(%rsp), %rcx
	cmpq	%rbx, %rcx
	je	.L2679
.L2820:
	leaq	264(%rsp), %rax
	cmpq	%rax, %rcx
	je	.L2679
	movq	%rbx, %rdx
	.p2align 4
	.p2align 3
.L2607:
	vmovsd	(%rax), %xmm0
	vucomisd	(%rdx), %xmm0
	cmova	%rax, %rdx
	addq	$8, %rax
	cmpq	%rax, %rcx
	jne	.L2607
	subq	%rbx, %rdx
	sarq	$3, %rdx
.L2604:
	testl	%r15d, %r15d
	jle	.L2612
	cmpl	$6, 100(%rsp)
	jbe	.L2681
	vpbroadcastd	%edx, %ymm0
	vmovapd	192(%rsp), %ymm4
	vmovapd	224(%rsp), %ymm6
	vpcmpd	$0, .LC48(%rip), %ymm0, %k1
	movl	68(%rsp), %eax
	vmovapd	.LC49(%rip), %ymm1{%k1}{z}
	kshiftrb	$4, %k1, %k1
	vfmadd231pd	.LC50(%rip), %ymm4, %ymm1
	vmovapd	.LC49(%rip), %ymm0{%k1}{z}
	vfmadd231pd	.LC50(%rip), %ymm6, %ymm0
	movl	%eax, %ecx
	vmovapd	%ymm1, 192(%rsp)
	vmovapd	%ymm0, 224(%rsp)
	cmpl	%r15d, %eax
	je	.L2612
.L2610:
	movl	%r15d, %esi
	subl	%ecx, %esi
	leal	-1(%rsi), %edi
	cmpl	$2, %edi
	jbe	.L2613
	vpbroadcastd	%eax, %xmm0
	vpaddd	.LC51(%rip), %xmm0, %xmm0
	vpbroadcastd	%edx, %xmm1
	leaq	192(%rsp,%rcx,8), %rcx
	vmovapd	(%rcx), %xmm6
	vmovapd	16(%rcx), %xmm4
	vpcmpd	$0, %xmm1, %xmm0, %k1
	vmovapd	.LC52(%rip), %xmm1{%k1}{z}
	kshiftrb	$2, %k1, %k1
	vfmadd231pd	.LC53(%rip), %xmm6, %xmm1
	vmovapd	.LC52(%rip), %xmm0{%k1}{z}
	vfmadd231pd	.LC53(%rip), %xmm4, %xmm0
	vmovapd	%xmm1, (%rcx)
	vmovapd	%xmm0, 16(%rcx)
	movl	%esi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %eax
	cmpl	%esi, %ecx
	je	.L2612
.L2613:
	movq	.LC44(%rip), %rsi
	vmovsd	.LC54(%rip), %xmm4
	movslq	%eax, %rcx
	vmulsd	192(%rsp,%rcx,8), %xmm4, %xmm0
	vmovq	%rsi, %xmm1
	cmpl	%edx, %eax
	je	.L2615
	vmovsd	%xmm8, %xmm8, %xmm1
.L2615:
	vaddsd	%xmm1, %xmm0, %xmm0
	vmovsd	%xmm0, 192(%rsp,%rcx,8)
	leal	1(%rax), %ecx
	cmpl	%ecx, %r15d
	jle	.L2612
	movq	.LC44(%rip), %rdi
	vmovsd	.LC54(%rip), %xmm6
	movslq	%ecx, %rsi
	vmulsd	192(%rsp,%rsi,8), %xmm6, %xmm0
	vmovq	%rdi, %xmm1
	cmpl	%edx, %ecx
	je	.L2616
	vmovsd	%xmm8, %xmm8, %xmm1
.L2616:
	vaddsd	%xmm1, %xmm0, %xmm0
	addl	$2, %eax
	vmovsd	%xmm0, 192(%rsp,%rsi,8)
	cmpl	%eax, %r15d
	jle	.L2612
	movq	.LC44(%rip), %rsi
	movslq	%eax, %rcx
	vmovsd	.LC54(%rip), %xmm4
	vmulsd	192(%rsp,%rcx,8), %xmm4, %xmm1
	vmovq	%rsi, %xmm0
	cmpl	%edx, %eax
	je	.L2617
	vmovsd	%xmm8, %xmm8, %xmm0
.L2617:
	vaddsd	%xmm1, %xmm0, %xmm0
	vmovsd	%xmm0, 192(%rsp,%rcx,8)
.L2612:
	cmpl	$1, 64(%rsp)
	je	.L2819
	movl	$1, 64(%rsp)
	jmp	.L2555
	.p2align 4
	.p2align 3
.L2584:
	vmovsd	%xmm9, %xmm9, %xmm1
	vmovsd	%xmm8, %xmm8, %xmm0
	vcomisd	%xmm9, %xmm6
	jbe	.L2653
	movl	0(%r13), %r14d
	vmovsd	%xmm9, %xmm9, %xmm4
	vmovsd	%xmm8, %xmm8, %xmm10
	jmp	.L2595
	.p2align 4
	.p2align 3
.L2816:
	movl	0(%r13), %r14d
	vmovsd	%xmm1, %xmm1, %xmm4
	vmovsd	%xmm0, %xmm0, %xmm10
	testl	%ebx, %ebx
	jg	.L2594
	jmp	.L2595
.L2813:
	movl	%r12d, (%rdx)
	jmp	.L2573
.L2664:
	xorl	%edi, %edi
	vmovsd	%xmm8, %xmm8, %xmm0
	xorl	%eax, %eax
	jmp	.L2566
.L2818:
	vucomisd	%xmm6, %xmm4
	jp	.L2602
	jne	.L2602
	vmovsd	48(%rsp), %xmm6
	vcomisd	%xmm10, %xmm6
	ja	.L2601
	movq	56(%rsp), %rcx
	cmpq	%rbx, %rcx
	jne	.L2820
.L2679:
	xorl	%edx, %edx
	jmp	.L2604
.L2666:
	vmovsd	%xmm10, %xmm10, %xmm4
	testl	%r15d, %r15d
	jg	.L2821
.L2669:
	vmovsd	%xmm8, %xmm8, %xmm10
	jmp	.L2581
.L2819:
	vpxor	%xmm0, %xmm0, %xmm0
	movq	120(%rsp), %rax
	vxorpd	%xmm1, %xmm1, %xmm1
	vmovdqa	%xmm0, 896(%rsp)
	vmovdqa	%xmm0, 912(%rsp)
	vmovdqa	%xmm0, 928(%rsp)
	vmovdqa	%xmm0, 944(%rsp)
	vbroadcastsd	.LC56(%rip), %zmm0
.L2620:
	vandpd	(%rax), %zmm0, %zmm2
	addq	$64, %rax
	vaddpd	%zmm2, %zmm1, %zmm1
	cmpq	%rax, %r14
	jne	.L2620
	movq	24(%rsp), %rdx
	movq	80(%rsp), %rax
	vmovapd	%ymm1, %ymm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vmovapd	%zmm1, 896(%rsp)
	addq	%rax, %rdx
	cmpq	%rax, %rdx
	je	.L2621
	leaq	904(%rsp), %rax
	cmpq	%rax, %rdx
	jne	.L2624
	jmp	.L2621
	.p2align 4
	.p2align 3
.L2822:
	vmovsd	(%rax), %xmm2
.L2624:
	addq	$8, %rax
	vminsd	%xmm0, %xmm2, %xmm0
	cmpq	%rax, %rdx
	jne	.L2822
.L2621:
	vmovsd	72(%rsp), %xmm7
	movq	112(%rsp), %r14
	leaq	176(%rsp), %r13
	leaq	152(%rsp), %rsi
	movq	%r13, %rdx
	leaq	120(%r14), %rdi
	vsubsd	%xmm0, %xmm7, %xmm0
	vmulsd	.LC43(%rip), %xmm0, %xmm0
	vmovsd	88(%rsp), %xmm7
	vunpcklpd	%xmm0, %xmm7, %xmm1
	vmovsd	%xmm0, 144(%rsp)
	vmovapd	%xmm1, 176(%rsp)
	vzeroupper
	call	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0
	movq	152(%rsp), %rbx
	vmovsd	144(%rsp), %xmm0
	popcntq	%rbx, %rax
	cmpl	8(%r14), %eax
	jne	.L2525
	movq	112(%rsp), %rax
	vmovsd	88(%rsp), %xmm7
	movq	%rbx, 168(%rsp)
	vmovsd	2848(%rax), %xmm1
	vcomisd	%xmm7, %xmm1
	jbe	.L2626
	vmovsd	%xmm7, 2848(%rax)
	movq	%rbx, 2856(%rax)
.L2626:
	movq	112(%rsp), %rax
	movq	208(%rax), %rdx
	movq	216(%rax), %rax
	movq	%rax, 144(%rsp)
	subq	%rdx, %rax
	cmpq	$1520, %rax
	jbe	.L2628
	vmovsd	(%rdx), %xmm1
	vcomisd	%xmm0, %xmm1
	jbe	.L2629
.L2628:
	movq	112(%rsp), %r14
	movq	%r13, %rsi
	vmovsd	%xmm0, 176(%rsp)
	movq	%rbx, 184(%rsp)
	leaq	208(%r14), %rdi
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	216(%r14), %rsi
	movq	208(%r14), %rdi
	movq	%rsi, %r8
	vmovsd	-16(%rsi), %xmm0
	movq	-8(%rsi), %r10
	subq	%rdi, %r8
	movq	%r8, %rdx
	sarq	$4, %rdx
	leaq	-1(%rdx), %rax
	subq	$2, %rdx
	movq	%rdx, %rcx
	shrq	$63, %rcx
	addq	%rdx, %rcx
	sarq	%rcx
	testq	%rax, %rax
	jg	.L2634
	jmp	.L2823
	.p2align 4
	.p2align 3
.L2631:
	cmpq	8(%r9), %r10
	seta	%dl
.L2633:
	salq	$4, %rax
	addq	%rdi, %rax
	testb	%dl, %dl
	je	.L2635
	vmovdqu	(%r9), %xmm7
	vmovdqu	%xmm7, (%rax)
	leaq	-1(%rcx), %rax
	movq	%rax, %rdx
	shrq	$63, %rdx
	addq	%rax, %rdx
	movq	%rcx, %rax
	sarq	%rdx
	testq	%rcx, %rcx
	jle	.L2824
	movq	%rdx, %rcx
.L2634:
	movq	%rcx, %r9
	salq	$4, %r9
	addq	%rdi, %r9
	vmovsd	(%r9), %xmm1
	vucomisd	%xmm1, %xmm0
	jp	.L2693
	je	.L2631
.L2693:
	vcomisd	%xmm1, %xmm0
	seta	%dl
	jmp	.L2633
.L2681:
	xorl	%ecx, %ecx
	xorl	%eax, %eax
	jmp	.L2610
.L2663:
	xorl	%edx, %edx
	xorl	%eax, %eax
	jmp	.L2561
.L2808:
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	movq	112(%rsp), %rcx
	cmpq	%rax, 2832(%rcx)
	jg	.L2530
	movb	$1, 2840(%rcx)
	jmp	.L2530
.L2823:
	leaq	-16(%rdi,%r8), %rax
.L2635:
	vmovsd	%xmm0, (%rax)
	movq	%r10, 8(%rax)
	cmpq	$1536, %r8
	ja	.L2825
.L2629:
	movq	112(%rsp), %rax
	movq	176(%rax), %rdx
	movq	184(%rax), %rax
	movq	%rax, 144(%rsp)
	subq	%rdx, %rax
	cmpq	$1520, %rax
	jbe	.L2638
	vmovsd	88(%rsp), %xmm7
	vcomisd	(%rdx), %xmm7
	jnb	.L2525
.L2638:
	movq	112(%rsp), %rcx
	movq	%rbx, %rax
	xorl	%edx, %edx
	movq	248(%rcx), %rdi
	divq	%rdi
	movq	240(%rcx), %rax
	movq	(%rax,%rdx,8), %rax
	movq	%rdx, %r8
	testq	%rax, %rax
	je	.L2641
	movq	(%rax), %rcx
	movq	8(%rcx), %rsi
.L2643:
	cmpq	%rsi, %rbx
	je	.L2525
	movq	(%rcx), %rcx
	testq	%rcx, %rcx
	je	.L2641
	movq	8(%rcx), %rsi
	xorl	%edx, %edx
	movq	%rsi, %rax
	divq	%rdi
	cmpq	%rdx, %r8
	je	.L2643
.L2641:
	vmovsd	88(%rsp), %xmm7
	movq	%rbx, 184(%rsp)
	movq	112(%rsp), %rbx
	movq	%r13, %rsi
	leaq	176(%rbx), %rdi
	vmovsd	%xmm7, 176(%rsp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	184(%rbx), %rax
	movq	176(%rbx), %rdx
	vmovsd	-16(%rax), %xmm0
	movq	-8(%rax), %r8
	subq	%rdx, %rax
	movq	%rax, %rdi
	movq	%rax, %rcx
	sarq	$4, %rdi
	leaq	-1(%rdi), %rax
	subq	$2, %rdi
	movq	%rdi, %rsi
	shrq	$63, %rsi
	addq	%rdi, %rsi
	sarq	%rsi
	testq	%rax, %rax
	jg	.L2648
	jmp	.L2826
	.p2align 4
	.p2align 3
.L2645:
	cmpq	%r8, 8(%rdi)
	setb	%cl
.L2647:
	salq	$4, %rax
	addq	%rdx, %rax
	testb	%cl, %cl
	je	.L2649
	vmovdqu	(%rdi), %xmm7
	vmovdqu	%xmm7, (%rax)
	leaq	-1(%rsi), %rax
	movq	%rax, %rcx
	shrq	$63, %rcx
	addq	%rax, %rcx
	movq	%rsi, %rax
	sarq	%rcx
	testq	%rsi, %rsi
	jle	.L2827
	movq	%rcx, %rsi
.L2648:
	movq	%rsi, %rdi
	salq	$4, %rdi
	addq	%rdx, %rdi
	vmovsd	(%rdi), %xmm1
	vucomisd	%xmm0, %xmm1
	jp	.L2694
	je	.L2645
.L2694:
	vcomisd	%xmm1, %xmm0
	seta	%cl
	jmp	.L2647
.L2825:
	leaq	-16(%rsi), %r14
	cmpq	$16, %r8
	jg	.L2828
.L2637:
	movq	112(%rsp), %rax
	movq	%r14, 216(%rax)
	jmp	.L2629
.L2828:
	vmovdqu	(%rdi), %xmm7
	movq	-16(%rsi), %rax
	movq	%r14, %rdx
	movq	-8(%rsi), %rcx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovq	%rax, %xmm0
	vmovdqu	%xmm7, -16(%rsi)
	xorl	%esi, %esi
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	jmp	.L2637
.L2827:
	movq	%rdi, %rax
.L2649:
	movq	112(%rsp), %rbx
	vmovsd	%xmm0, (%rax)
	movq	%r8, 8(%rax)
	leaq	168(%rsp), %rsi
	leaq	240(%rbx), %r13
	movq	%r13, %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
	movq	184(%rbx), %rax
	movq	176(%rbx), %rdx
	movq	%rax, 144(%rsp)
	subq	%rdx, %rax
	cmpq	$1536, %rax
	jbe	.L2525
	movq	8(%rdx), %rsi
	movq	%r13, %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE8_M_eraseESt17integral_constantIbLb1EERKm.isra.0
	movq	112(%rsp), %rcx
	movq	184(%rcx), %rax
	movq	176(%rcx), %rdi
	movq	%rax, %rdx
	leaq	-16(%rax), %rbx
	subq	%rdi, %rdx
	cmpq	$16, %rdx
	jg	.L2829
.L2650:
	movq	112(%rsp), %rax
	movq	%rbx, 184(%rax)
	jmp	.L2525
.L2826:
	leaq	-16(%rdx,%rcx), %rax
	jmp	.L2649
.L2829:
	vmovdqu	(%rdi), %xmm7
	movq	-16(%rax), %rdx
	xorl	%esi, %esi
	movq	-8(%rax), %rcx
	vmovq	%rdx, %xmm0
	movq	%rbx, %rdx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm7, -16(%rax)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	jmp	.L2650
	.p2align 4
	.p2align 3
.L2662:
	xorl	%edx, %edx
	xorl	%eax, %eax
	jmp	.L2556
.L2811:
	leal	-1(%r15), %eax
	movl	%eax, 100(%rsp)
	jmp	.L2558
.L2824:
	movq	%r9, %rax
	jmp	.L2635
.L2815:
	call	__stack_chk_fail@PLT
	.p2align 4
	.p2align 3
.L2658:
	vmovsd	.LC1(%rip), %xmm4
	movq	$4, 40(%rsp)
	movl	$1, %edi
	vmovsd	%xmm4, 72(%rsp)
	vmovsd	%xmm4, %xmm4, %xmm3
	jmp	.L2531
	.cfi_endproc
.LFE8934:
	.size	_ZN9Optimizer8evaluateEmb.constprop.0, .-_ZN9Optimizer8evaluateEmb.constprop.0
	.section	.rodata._ZN9Optimizer14spectral_seedsEv.str1.1,"aMS",@progbits,1
.LC61:
	.string	"spectral_scans="
.LC62:
	.string	" seeds="
.LC63:
	.string	" "
	.section	.text._ZN9Optimizer14spectral_seedsEv,"axG",@progbits,_ZN9Optimizer14spectral_seedsEv,comdat
	.align 2
	.p2align 4
	.weak	_ZN9Optimizer14spectral_seedsEv
	.type	_ZN9Optimizer14spectral_seedsEv, @function
_ZN9Optimizer14spectral_seedsEv:
.LFB6024:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA6024
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	vxorpd	%xmm4, %xmm4, %xmm4
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	.cfi_offset 15, -24
	.cfi_offset 14, -32
	.cfi_offset 13, -40
	.cfi_offset 12, -48
	.cfi_offset 3, -56
	movq	%rsi, %r15
	andq	$-64, %rsp
	subq	$320, %rsp
	vmovsd	.LC26(%rip), %xmm1
	movq	2824(%rsi), %rdx
	movq	%rdi, 24(%rsp)
	vmovsd	.LC59(%rip), %xmm2
	movq	%fs:40, %rax
	movq	%rax, 312(%rsp)
	xorl	%eax, %eax
	movq	2832(%rsi), %rax
	subq	%rdx, %rax
	vcvtsi2sdq	%rax, %xmm4, %xmm0
	vdivsd	%xmm1, %xmm0, %xmm0
	movabsq	$5000000000, %rax
	vmulsd	.LC58(%rip), %xmm0, %xmm0
	vcomisd	%xmm0, %xmm2
	jbe	.L2831
	vmulsd	%xmm1, %xmm0, %xmm0
	vcvttsd2siq	%xmm0, %rax
.L2831:
	movslq	4(%r15), %rbx
	addq	%rdx, %rax
	movq	%rax, 32(%rsp)
	movq	%rbx, %rax
	shrq	$61, %rax
	jne	.L3036
	leaq	0(,%rbx,4), %r12
	testq	%rbx, %rbx
	je	.L2938
	movq	%r12, %rdi
.LEHB26:
	call	_Znwm@PLT
.LEHE26:
	cmpq	$1, %rbx
	movl	4(%r15), %ebx
	movq	%rax, %rsi
	movq	%rax, 80(%rsp)
	leaq	(%rax,%r12), %rax
	movq	%rax, %r14
	movq	%rax, 16(%rsp)
	movl	$0, (%rsi)
	leaq	4(%rsi), %rdi
	je	.L2836
	cmpq	%rdi, %rax
	je	.L2836
	leaq	-4(%r12), %rdx
	xorl	%esi, %esi
	call	memset@PLT
	movq	%r14, %rdi
.L2836:
	testl	%ebx, %ebx
	jle	.L2834
	leal	-1(%rbx), %eax
	cmpl	$14, %eax
	jbe	.L2940
	vmovdqa32	.LC57(%rip), %zmm0
	vpbroadcastd	.LC64(%rip), %zmm1
	movl	%ebx, %edx
	movq	80(%rsp), %rax
	shrl	$4, %edx
	decl	%edx
	salq	$6, %rdx
	leaq	64(%rax,%rdx), %rdx
.L2841:
	vmovdqa32	%zmm0, %zmm2
	addq	$64, %rax
	vpaddd	%zmm1, %zmm0, %zmm0
	vmovdqu32	%zmm2, -64(%rax)
	cmpq	%rax, %rdx
	jne	.L2841
	movl	%ebx, %edx
	andl	$-16, %edx
	movl	%edx, %eax
	cmpl	%ebx, %edx
	je	.L3029
.L2840:
	movl	%ebx, %ecx
	subl	%edx, %ecx
	leal	-1(%rcx), %esi
	cmpl	$6, %esi
	jbe	.L2844
	vpbroadcastd	%eax, %ymm0
	vpaddd	.LC48(%rip), %ymm0, %ymm0
	movq	80(%rsp), %rsi
	vmovdqu	%ymm0, (%rsi,%rdx,4)
	movl	%ecx, %edx
	andl	$-8, %edx
	addl	%edx, %eax
	cmpl	%ecx, %edx
	je	.L3029
.L2844:
	movq	80(%rsp), %rsi
	movslq	%eax, %rdx
	leal	1(%rax), %ecx
	salq	$2, %rdx
	movl	%eax, (%rsi,%rdx)
	cmpl	%ebx, %ecx
	jge	.L3029
	movl	%ecx, 4(%rsi,%rdx)
	leal	2(%rax), %ecx
	cmpl	%ebx, %ecx
	jge	.L3029
	movl	%ecx, 8(%rsi,%rdx)
	leal	3(%rax), %ecx
	cmpl	%ebx, %ecx
	jge	.L3029
	movl	%ecx, 12(%rsi,%rdx)
	leal	4(%rax), %ecx
	cmpl	%ecx, %ebx
	jle	.L3029
	movl	%ecx, 16(%rsi,%rdx)
	leal	5(%rax), %ecx
	cmpl	%ebx, %ecx
	jge	.L3029
	addl	$6, %eax
	movl	%ecx, 20(%rsi,%rdx)
	cmpl	%ebx, %eax
	jge	.L3029
	movl	%eax, 24(%rsi,%rdx)
	vzeroupper
.L2834:
	movq	%rdi, %rsi
	movq	80(%rsp), %rdi
	leaq	296(%r15), %rdx
	call	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPiSt6vectorIiSaIiEEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SA_OT0_
	movl	12(%r15), %eax
	addl	$2, %eax
	cltq
	movq	%rax, %rsi
	shrq	$58, %rsi
	jne	.L3037
	vpxor	%xmm0, %xmm0, %xmm0
	movq	%rax, %rbx
	vmovdqu	%xmm0, 152(%rsp)
	salq	$5, %rbx
	testq	%rax, %rax
	je	.L2846
	movq	%rbx, %rdi
.LEHB27:
	call	_Znwm@PLT
.LEHE27:
	addq	%rax, %rbx
	movq	%rax, 56(%rsp)
	movq	%rax, 144(%rsp)
	vpxor	%xmm0, %xmm0, %xmm0
	movq	%rbx, 48(%rsp)
	movq	%rbx, 160(%rsp)
.L2847:
	vmovdqu	%xmm0, (%rax)
	movq	$0, 16(%rax)
	addq	$32, %rax
	cmpq	48(%rsp), %rax
	jne	.L2847
.L2934:
	movq	48(%rsp), %rax
	movq	%rax, 152(%rsp)
	movl	8(%r15), %eax
	testl	%eax, %eax
	jle	.L2941
	movl	4(%r15), %ecx
	movl	$1, 44(%rsp)
	movq	$0, 72(%rsp)
.L2900:
	movl	$1, %eax
	movl	44(%rsp), %esi
	movq	24(%r15), %rdx
	movl	%esi, %ebx
	shlx	%rbx, %rax, %rax
	decq	%rax
	movq	%rax, 88(%rsp)
	leal	-1(%rsi), %eax
	cmpl	$14, %eax
	jbe	.L2942
	movq	80(%rsp), %rax
	shrl	$4, %esi
	vpxor	%xmm1, %xmm1, %xmm1
	kxnorw	%k1, %k1, %k1
	decl	%esi
	salq	$6, %rsi
	leaq	64(%rax,%rsi), %rsi
.L2850:
	vmovdqu32	(%rax), %zmm4
	kmovw	%k1, %k2
	addq	$64, %rax
	vpgatherdd	(%rdx,%zmm4,4), %zmm0{%k2}
	vpxord	%zmm0, %zmm1, %zmm1
	cmpq	%rsi, %rax
	jne	.L2850
	vextracti32x8	$0x1, %zmm1, %ymm0
	movl	44(%rsp), %ebx
	vpxor	%ymm1, %ymm0, %ymm1
	vextracti128	$0x1, %ymm1, %xmm0
	vpxor	%xmm1, %xmm0, %xmm0
	vpsrldq	$8, %xmm0, %xmm1
	movl	%ebx, %esi
	vpxor	%xmm1, %xmm0, %xmm0
	andl	$-16, %esi
	vpsrldq	$4, %xmm0, %xmm1
	vpxor	%xmm1, %xmm0, %xmm0
	vmovd	%xmm0, %r14d
	movl	%esi, %eax
	cmpl	%esi, %ebx
	je	.L2851
.L2849:
	movl	44(%rsp), %edi
	subl	%esi, %edi
	leal	-1(%rdi), %r8d
	cmpl	$6, %r8d
	jbe	.L2852
	movq	80(%rsp), %rbx
	kmovb	.LC65(%rip), %k3
	vmovdqu	(%rbx,%rsi,4), %ymm0
	vpgatherdd	(%rdx,%ymm0,4), %ymm1{%k3}
	vextracti128	$0x1, %ymm1, %xmm0
	vpxor	%xmm1, %xmm0, %xmm0
	vpsrldq	$8, %xmm0, %xmm1
	vpxor	%xmm1, %xmm0, %xmm0
	vpsrldq	$4, %xmm0, %xmm1
	vpxor	%xmm1, %xmm0, %xmm0
	vmovd	%xmm0, %esi
	xorl	%esi, %r14d
	movl	%edi, %esi
	andl	$-8, %esi
	addl	%esi, %eax
	cmpl	%edi, %esi
	je	.L2851
.L2852:
	movq	80(%rsp), %rbx
	movslq	%eax, %rdi
	movl	44(%rsp), %r11d
	leaq	0(,%rdi,4), %rsi
	movslq	(%rbx,%rdi,4), %rdi
	xorl	(%rdx,%rdi,4), %r14d
	leal	1(%rax), %edi
	cmpl	%r11d, %edi
	jge	.L2851
	movslq	4(%rbx,%rsi), %rdi
	xorl	(%rdx,%rdi,4), %r14d
	leal	2(%rax), %edi
	cmpl	%r11d, %edi
	jge	.L2851
	movslq	8(%rbx,%rsi), %rdi
	xorl	(%rdx,%rdi,4), %r14d
	leal	3(%rax), %edi
	cmpl	%r11d, %edi
	jge	.L2851
	movslq	12(%rbx,%rsi), %rdi
	xorl	(%rdx,%rdi,4), %r14d
	leal	4(%rax), %edi
	cmpl	%r11d, %edi
	jge	.L2851
	movslq	16(%rbx,%rsi), %rdi
	xorl	(%rdx,%rdi,4), %r14d
	leal	5(%rax), %edi
	cmpl	%r11d, %edi
	jge	.L2851
	movslq	20(%rbx,%rsi), %rdi
	addl	$6, %eax
	xorl	(%rdx,%rdi,4), %r14d
	cmpl	%r11d, %eax
	jge	.L2851
	movslq	24(%rbx,%rsi), %rax
	xorl	(%rdx,%rax,4), %r14d
.L2851:
	movl	$1, %eax
	shlx	%rcx, %rax, %rax
	cmpq	%rax, 88(%rsp)
	jnb	.L2898
	.p2align 4
	.p2align 3
.L2899:
	movl	2800(%r15), %eax
	movl	%r14d, %r8d
	cmpl	%eax, (%r15)
	jle	.L2854
	imull	$-1640531535, %r14d, %r8d
	movl	$32, %edx
	subl	%eax, %edx
	shrx	%edx, %r8d, %r8d
.L2854:
	movq	72(%r15), %rax
	leaq	(%rax,%r8,4), %rax
	salq	$6, %r8
	addq	96(%r15), %r8
	cmpl	%r14d, (%rax)
	je	.L2855
	movq	48(%r15), %rdx
	movq	56(%r15), %rsi
	incq	2816(%r15)
	movl	%r14d, (%rax)
	cmpq	%rsi, %rdx
	je	.L2944
	vmovsd	.LC1(%rip), %xmm0
	vmovsd	%xmm0, %xmm0, %xmm4
	vmovsd	%xmm0, %xmm0, %xmm7
	vmovsd	%xmm0, %xmm0, %xmm2
	vmovsd	%xmm0, %xmm0, %xmm6
	vmovsd	%xmm0, %xmm0, %xmm3
	vmovsd	%xmm0, %xmm0, %xmm5
	vmovsd	%xmm0, %xmm0, %xmm1
	.p2align 4
	.p2align 3
.L2857:
	movl	(%rdx), %edi
	xorl	%eax, %eax
	testl	%edi, %edi
	jle	.L2861
	movl	4(%rdx), %eax
	andl	%r14d, %eax
	popcntl	%eax, %eax
	andl	$1, %eax
	cmpl	$1, %edi
	je	.L2861
	movl	8(%rdx), %ecx
	andl	%r14d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	addl	%ecx, %ecx
	orl	%ecx, %eax
	cmpl	$2, %edi
	je	.L2861
	movl	12(%rdx), %ecx
	andl	%r14d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	sall	$2, %ecx
	orl	%ecx, %eax
.L2861:
	cltq
	movq	%rax, %rcx
	salq	$6, %rcx
	vmulsd	224(%rcx,%rdx), %xmm1, %xmm1
	vmulsd	232(%rdx,%rcx), %xmm5, %xmm5
	addq	$736, %rdx
	vmulsd	-496(%rdx,%rcx), %xmm3, %xmm3
	vmulsd	-488(%rdx,%rcx), %xmm6, %xmm6
	vmulsd	-480(%rdx,%rcx), %xmm2, %xmm2
	vmulsd	-472(%rdx,%rcx), %xmm7, %xmm7
	vmulsd	-464(%rdx,%rcx), %xmm4, %xmm4
	vmulsd	-456(%rdx,%rcx), %xmm0, %xmm0
	cmpq	%rdx, %rsi
	jne	.L2857
	vunpcklpd	%xmm0, %xmm4, %xmm4
	vunpcklpd	%xmm7, %xmm2, %xmm2
	vunpcklpd	%xmm6, %xmm3, %xmm3
	vunpcklpd	%xmm5, %xmm1, %xmm0
	vinsertf128	$0x1, %xmm4, %ymm2, %ymm2
	vinsertf128	$0x1, %xmm3, %ymm0, %ymm0
	vinsertf64x4	$0x1, %ymm2, %zmm0, %zmm0
.L2856:
	vmovupd	%zmm0, (%r8)
.L2855:
	movl	12(%r15), %edx
	testl	%edx, %edx
	jle	.L2862
	vmovsd	(%r8), %xmm3
	vminsd	.LC1(%rip), %xmm3, %xmm2
	vmaxsd	.LC3(%rip), %xmm3, %xmm1
	vaddsd	.LC4(%rip), %xmm3, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, 256(%rsp)
	cmpl	$1, %edx
	je	.L2865
	vmovsd	8(%r8), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, 264(%rsp)
	cmpl	$2, %edx
	je	.L2865
	vmovsd	16(%r8), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, 272(%rsp)
	cmpl	$3, %edx
	je	.L2865
	vmovsd	24(%r8), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, 280(%rsp)
	cmpl	$4, %edx
	je	.L2865
	vmovsd	32(%r8), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, 288(%rsp)
	cmpl	$5, %edx
	je	.L2865
	vmovsd	40(%r8), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, 296(%rsp)
.L2865:
	vxorpd	.LC6(%rip), %xmm1, %xmm4
	vandpd	.LC5(%rip), %xmm0, %xmm0
	vxorpd	.LC6(%rip), %xmm2, %xmm3
	vxorpd	.LC6(%rip), %xmm0, %xmm0
	vcmpnltsd	%xmm4, %xmm2, %xmm2
	vxorpd	%xmm4, %xmm4, %xmm4
	vblendvpd	%xmm2, %xmm3, %xmm1, %xmm1
	vcvtsi2sdl	%edx, %xmm4, %xmm2
	vdivsd	%xmm2, %xmm0, %xmm0
	vunpcklpd	%xmm0, %xmm1, %xmm1
	vmovapd	%xmm1, 240(%rsp)
.L2877:
	movq	56(%rsp), %rbx
	leaq	240(%rsp), %rax
	xorl	%r13d, %r13d
	xorl	%esi, %esi
	movq	%rax, 104(%rsp)
	leaq	176(%rsp), %rax
	xorl	%r12d, %r12d
	movq	%rax, 96(%rsp)
	.p2align 4
	.p2align 3
.L2892:
	movq	(%rbx), %rcx
	movq	8(%rbx), %rax
	subq	%rcx, %rax
	cmpq	$752, %rax
	jbe	.L2880
	movq	104(%rsp), %rax
	vmovsd	(%rax,%r13,8), %xmm0
	vcomisd	(%rcx), %xmm0
	jnb	.L2881
.L2880:
	testb	%sil, %sil
	je	.L3038
.L2882:
	movq	104(%rsp), %rax
	movq	96(%rsp), %rsi
	movq	%rbx, %rdi
	movq	%r12, 184(%rsp)
	vmovsd	(%rax,%r13,8), %xmm0
	vmovsd	%xmm0, 176(%rsp)
	vzeroupper
.LEHB28:
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
.LEHE28:
	movq	8(%rbx), %r10
	movq	(%rbx), %r8
	movq	%r10, %rsi
	vmovsd	-16(%r10), %xmm1
	movq	-8(%r10), %r9
	subq	%r8, %rsi
	movq	%rsi, %rdx
	sarq	$4, %rdx
	leaq	-1(%rdx), %rax
	subq	$2, %rdx
	movq	%rdx, %rcx
	shrq	$63, %rcx
	addq	%rdx, %rcx
	sarq	%rcx
	testq	%rax, %rax
	jg	.L2888
	jmp	.L3039
	.p2align 4
	.p2align 3
.L2885:
	cmpq	8(%rdx), %r9
	seta	%dil
.L2887:
	salq	$4, %rax
	addq	%r8, %rax
	testb	%dil, %dil
	je	.L2889
	vmovdqu	(%rdx), %xmm6
	leaq	-1(%rcx), %rdi
	vmovdqu	%xmm6, (%rax)
	movq	%rdi, %rax
	shrq	$63, %rax
	addq	%rax, %rdi
	movq	%rcx, %rax
	sarq	%rdi
	testq	%rcx, %rcx
	jle	.L3040
	movq	%rdi, %rcx
.L2888:
	movq	%rcx, %rdx
	salq	$4, %rdx
	addq	%r8, %rdx
	vmovsd	(%rdx), %xmm0
	vucomisd	%xmm0, %xmm1
	jp	.L2964
	je	.L2885
.L2964:
	vcomisd	%xmm0, %xmm1
	seta	%dil
	jmp	.L2887
	.p2align 4
	.p2align 3
.L3040:
	movq	%rdx, %rax
.L2889:
	vmovsd	%xmm1, (%rax)
	movq	%r9, 8(%rax)
	cmpq	$768, %rsi
	ja	.L2890
.L3034:
	movl	$1, %esi
	movl	12(%r15), %edx
.L2881:
	incq	%r13
	addq	$32, %rbx
	leal	-1(%r13), %eax
	cmpl	%edx, %eax
	jle	.L2892
.L2893:
	movq	88(%rsp), %rsi
	xorl	%edx, %edx
	blsi	%rsi, %rcx
	movq	%rsi, %rax
	leaq	(%rcx,%rsi), %rbx
	xorq	%rbx, %rax
	shrq	$2, %rax
	divq	%rcx
	movl	4(%r15), %ecx
	orq	%rax, %rbx
	movl	$1, %eax
	xorq	%rbx, %rsi
	shlx	%rcx, %rax, %rax
	movq	%rsi, %rdx
	cmpq	%rbx, %rax
	jbe	.L2898
	cmpq	88(%rsp), %rbx
	je	.L2894
	movq	24(%r15), %rax
	movq	80(%rsp), %rsi
	.p2align 4
	.p2align 3
.L2895:
	tzcntq	%rdx, %rcx
	movslq	(%rsi,%rcx,4), %rcx
	xorl	(%rax,%rcx,4), %r14d
	blsr	%rdx, %rdx
	jne	.L2895
.L2894:
	incq	72(%rsp)
	movq	72(%rsp), %rax
	testl	$4095, %eax
	je	.L3041
.L2935:
	movq	%rbx, 88(%rsp)
	jmp	.L2899
	.p2align 4
	.p2align 3
.L2890:
	leaq	-16(%r10), %rax
	cmpq	$16, %rsi
	jg	.L3042
.L2891:
	movq	%rax, 8(%rbx)
	jmp	.L3034
	.p2align 4
	.p2align 3
.L3038:
	movq	88(%rsp), %rax
	movq	80(%rsp), %rsi
	movl	$1, %ecx
	.p2align 4
	.p2align 3
.L2883:
	tzcntq	%rax, %rdx
	movl	(%rsi,%rdx,4), %edx
	shlx	%rdx, %rcx, %rdx
	orq	%rdx, %r12
	blsr	%rax, %rax
	jne	.L2883
	jmp	.L2882
	.p2align 4
	.p2align 3
.L3042:
	vmovdqu	(%r8), %xmm4
	movq	-16(%r10), %rdx
	xorl	%esi, %esi
	movq	%r8, %rdi
	movq	-8(%r10), %rcx
	movq	%rax, 64(%rsp)
	vmovq	%rdx, %xmm0
	movq	%rax, %rdx
	subq	%r8, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm4, -16(%r10)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	movq	64(%rsp), %rax
	jmp	.L2891
.L3039:
	leaq	-16(%r8,%rsi), %rax
	jmp	.L2889
.L3041:
	vzeroupper
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	cmpq	%rax, 32(%rsp)
	jle	.L2848
	movl	4(%r15), %ecx
	movl	$1, %eax
	shlx	%rcx, %rax, %rax
	cmpq	%rax, %rbx
	jb	.L2935
.L2898:
	incl	44(%rsp)
	movl	44(%rsp), %eax
	cmpl	%eax, 8(%r15)
	jge	.L2900
.L2848:
	leaq	224(%rsp), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$1, 184(%rsp)
	movq	$0, 192(%rsp)
	movq	%rax, 64(%rsp)
	movq	%rax, 176(%rsp)
	movq	$0, 200(%rsp)
	movl	$0x3f800000, 208(%rsp)
	movq	$0, 216(%rsp)
	movq	$0, 224(%rsp)
	movq	24(%rsp), %rax
	vmovdqu	%xmm0, (%rax)
	movq	$0, 16(%rax)
	movq	56(%rsp), %rax
	movq	%rax, 96(%rsp)
	cmpq	48(%rsp), %rax
	je	.L2902
	.p2align 4
	.p2align 3
.L2914:
	movq	96(%rsp), %rsi
	movq	8(%rsi), %rax
	movq	(%rsi), %rdi
	cmpq	%rdi, %rax
	je	.L2907
	cmpb	$0, 2840(%r15)
	jne	.L2907
	movq	8(%rdi), %rdx
	leaq	-16(%rax), %rbx
	movq	%rdx, 120(%rsp)
	movq	%rax, %rdx
	subq	%rdi, %rdx
	cmpq	$16, %rdx
	jg	.L3043
	vzeroupper
.L2915:
	movq	96(%rsp), %rax
	leaq	120(%rsp), %rsi
	movq	%rbx, 8(%rax)
	leaq	176(%rsp), %rax
	movq	%rax, %rdi
	movq	%rax, 88(%rsp)
.LEHB29:
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
	testb	%dl, %dl
	je	.L2914
	movq	120(%rsp), %r12
	movl	8(%r15), %edx
	popcntq	%r12, %rax
	movq	%r12, %r14
	movl	%eax, %ecx
	cmpl	%edx, %eax
	jge	.L2905
	.p2align 4
	.p2align 3
.L2904:
	cmpb	$0, 2840(%r15)
	jne	.L2914
	movl	4(%r15), %eax
	testl	%eax, %eax
	jle	.L3044
	vmovsd	.LC1(%rip), %xmm4
	xorl	%r14d, %r14d
	xorl	%ebx, %ebx
	vmovsd	%xmm4, 104(%rsp)
	.p2align 4
	.p2align 3
.L2910:
	btq	%rbx, %r12
	jc	.L2908
	movq	%r12, %r13
	movq	%r15, %rdi
	btsq	%rbx, %r13
	movq	%r13, %rsi
	call	_ZN9Optimizer8evaluateEmb.constprop.0
	vmovsd	104(%rsp), %xmm7
	movl	4(%r15), %eax
	vminsd	%xmm7, %xmm0, %xmm5
	vcomisd	%xmm0, %xmm7
	cmova	%r13, %r14
	vmovsd	%xmm5, 104(%rsp)
.L2908:
	incl	%ebx
	cmpl	%eax, %ebx
	jl	.L2910
	movl	8(%r15), %edx
	popcntq	%r14, %rax
	movq	%r14, 120(%rsp)
	movl	%eax, %ecx
	cmpl	%edx, %eax
	jge	.L2905
	movq	%r14, %r12
	jmp	.L2904
.L3044:
	movq	$0, 120(%rsp)
	testl	%edx, %edx
	jg	.L2914
	xorl	%ecx, %ecx
	xorl	%r14d, %r14d
.L2905:
	cmpl	%ecx, %edx
	jne	.L2914
	movq	%r14, %rsi
	movq	%r15, %rdi
	call	_ZN9Optimizer8evaluateEmb.constprop.0
	movq	24(%rsp), %rdi
	leaq	128(%rsp), %rsi
	vmovsd	%xmm0, 128(%rsp)
	movq	%r14, 136(%rsp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	jmp	.L2914
.L3043:
	vmovdqu	(%rdi), %xmm4
	movq	-16(%rax), %rdx
	xorl	%esi, %esi
	movq	-8(%rax), %rcx
	vmovq	%rdx, %xmm0
	movq	%rbx, %rdx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm4, -16(%rax)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	jmp	.L2915
.L2862:
	vxorpd	%xmm4, %xmm4, %xmm4
	vmovsd	.LC3(%rip), %xmm5
	vcvtsi2sdl	%edx, %xmm4, %xmm0
	vmovsd	.LC7(%rip), %xmm4
	vdivsd	%xmm0, %xmm4, %xmm0
	vunpcklpd	%xmm0, %xmm5, %xmm0
	vmovapd	%xmm0, 240(%rsp)
	cmpl	$-1, %edx
	jl	.L2893
	jmp	.L2877
.L2907:
	addq	$32, 96(%rsp)
	movq	96(%rsp), %rax
	cmpq	%rax, 48(%rsp)
	jne	.L2914
.L2902:
	leaq	_ZSt4cerr(%rip), %r12
	leaq	176(%rsp), %rax
	movl	$15, %edx
	leaq	.LC61(%rip), %rsi
	movq	%r12, %rdi
	movq	%rax, 88(%rsp)
	vzeroupper
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	72(%rsp), %rsi
	leaq	176(%rsp), %rax
	movq	%r12, %rdi
	movq	%rax, 88(%rsp)
	call	_ZNSo9_M_insertImEERSoT_@PLT
	movq	%rax, %r12
	movl	$7, %edx
	leaq	176(%rsp), %rax
	leaq	.LC62(%rip), %rsi
	movq	%r12, %rdi
	movq	%rax, 88(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	24(%rsp), %rsi
	movq	%r12, %rdi
	movq	8(%rsi), %rax
	subq	(%rsi), %rax
	sarq	$4, %rax
	movq	%rax, %rsi
	leaq	176(%rsp), %rax
	movq	%rax, 88(%rsp)
	call	_ZNSo9_M_insertImEERSoT_@PLT
	movq	%rax, %rdi
	movl	$1, %edx
	leaq	176(%rsp), %rax
	leaq	.LC63(%rip), %rsi
	movq	%rax, 88(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
.LEHE29:
	movq	192(%rsp), %rbx
	testq	%rbx, %rbx
	je	.L2920
.L2917:
	movq	%rbx, %rdi
	movq	(%rbx), %rbx
	movl	$16, %esi
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L2917
.L2920:
	movq	184(%rsp), %rax
	movq	176(%rsp), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	184(%rsp), %rsi
	movq	$0, 200(%rsp)
	movq	$0, 192(%rsp)
	movq	176(%rsp), %rdi
	cmpq	64(%rsp), %rdi
	je	.L2918
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L2918:
	movq	56(%rsp), %rax
	movq	48(%rsp), %rsi
	movq	%rax, %rbx
	cmpq	%rsi, %rax
	je	.L2926
.L2921:
	movq	(%rbx), %rdi
	testq	%rdi, %rdi
	je	.L2924
	movq	16(%rbx), %rsi
	addq	$32, %rbx
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	cmpq	%rbx, 48(%rsp)
	jne	.L2921
.L2926:
	cmpq	$0, 56(%rsp)
	je	.L2923
.L2922:
	movq	48(%rsp), %rsi
	movq	56(%rsp), %rdi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L2923:
	movq	80(%rsp), %rax
	testq	%rax, %rax
	je	.L2830
	movq	16(%rsp), %rsi
	movq	%rax, %rdi
	subq	%rax, %rsi
	call	_ZdlPvm@PLT
.L2830:
	movq	312(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L3045
	movq	24(%rsp), %rax
	leaq	-40(%rbp), %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
.L2944:
	.cfi_restore_state
	vmovapd	.LC2(%rip), %zmm0
	jmp	.L2856
.L2924:
	addq	$32, %rbx
	cmpq	48(%rsp), %rbx
	jne	.L2921
	cmpq	$0, 56(%rsp)
	jne	.L2922
	jmp	.L2923
.L2942:
	xorl	%esi, %esi
	xorl	%eax, %eax
	xorl	%r14d, %r14d
	jmp	.L2849
.L3029:
	vzeroupper
	jmp	.L2834
.L2938:
	movq	$0, 80(%rsp)
	xorl	%edi, %edi
	movq	$0, 16(%rsp)
	jmp	.L2834
.L2846:
	movq	$0, 144(%rsp)
	movq	$0, 160(%rsp)
	movq	$0, 56(%rsp)
	movq	$0, 48(%rsp)
	jmp	.L2934
.L2940:
	xorl	%edx, %edx
	xorl	%eax, %eax
	jmp	.L2840
.L3036:
	leaq	.LC11(%rip), %rdi
.LEHB30:
	call	_ZSt20__throw_length_errorPKc@PLT
.LEHE30:
.L3045:
	call	__stack_chk_fail@PLT
	.p2align 4
	.p2align 3
.L2941:
	movq	$0, 72(%rsp)
	jmp	.L2848
.L3037:
	leaq	.LC11(%rip), %rdi
.LEHB31:
	call	_ZSt20__throw_length_errorPKc@PLT
.LEHE31:
.L2960:
	endbr64
	movq	%rax, %r12
	jmp	.L2931
.L2962:
	endbr64
	movq	%rax, %r12
	jmp	.L2928
.L2961:
	endbr64
	movq	%rax, %r12
	jmp	.L2930
.L2928:
	movq	24(%rsp), %rax
	movq	(%rax), %rdi
	movq	16(%rax), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L3031
	vzeroupper
	call	_ZdlPvm@PLT
.L2929:
	movq	88(%rsp), %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED1Ev
.L2930:
	leaq	144(%rsp), %rdi
	vzeroupper
	call	_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED1Ev
.L2931:
	movq	16(%rsp), %rsi
	subq	80(%rsp), %rsi
	cmpq	$0, 80(%rsp)
	je	.L3032
	movq	80(%rsp), %rdi
	vzeroupper
	call	_ZdlPvm@PLT
.L2932:
	movq	%r12, %rdi
.LEHB32:
	call	_Unwind_Resume@PLT
.LEHE32:
.L3031:
	vzeroupper
	jmp	.L2929
.L3032:
	vzeroupper
	jmp	.L2932
	.cfi_endproc
.LFE6024:
	.section	.gcc_except_table
.LLSDA6024:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE6024-.LLSDACSB6024
.LLSDACSB6024:
	.uleb128 .LEHB26-.LFB6024
	.uleb128 .LEHE26-.LEHB26
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB27-.LFB6024
	.uleb128 .LEHE27-.LEHB27
	.uleb128 .L2960-.LFB6024
	.uleb128 0
	.uleb128 .LEHB28-.LFB6024
	.uleb128 .LEHE28-.LEHB28
	.uleb128 .L2961-.LFB6024
	.uleb128 0
	.uleb128 .LEHB29-.LFB6024
	.uleb128 .LEHE29-.LEHB29
	.uleb128 .L2962-.LFB6024
	.uleb128 0
	.uleb128 .LEHB30-.LFB6024
	.uleb128 .LEHE30-.LEHB30
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB31-.LFB6024
	.uleb128 .LEHE31-.LEHB31
	.uleb128 .L2960-.LFB6024
	.uleb128 0
	.uleb128 .LEHB32-.LFB6024
	.uleb128 .LEHE32-.LEHB32
	.uleb128 0
	.uleb128 0
.LLSDACSE6024:
	.section	.text._ZN9Optimizer14spectral_seedsEv,"axG",@progbits,_ZN9Optimizer14spectral_seedsEv,comdat
	.size	_ZN9Optimizer14spectral_seedsEv, .-_ZN9Optimizer14spectral_seedsEv
	.section	.rodata._ZN9Optimizer14informed_seedsEv.str1.1,"aMS",@progbits,1
.LC79:
	.string	"informed_targets="
	.section	.text._ZN9Optimizer14informed_seedsEv,"axG",@progbits,_ZN9Optimizer14informed_seedsEv,comdat
	.align 2
	.p2align 4
	.weak	_ZN9Optimizer14informed_seedsEv
	.type	_ZN9Optimizer14informed_seedsEv, @function
_ZN9Optimizer14informed_seedsEv:
.LFB6027:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA6027
	endbr64
	leaq	8(%rsp), %r10
	.cfi_def_cfa 10, 0
	andq	$-64, %rsp
	pushq	-8(%r10)
	pushq	%rbp
	movq	%rsp, %rbp
	.cfi_escape 0x10,0x6,0x2,0x76,0
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%r10
	.cfi_escape 0xf,0x3,0x76,0x58,0x6
	.cfi_escape 0x10,0xf,0x2,0x76,0x78
	.cfi_escape 0x10,0xe,0x2,0x76,0x70
	.cfi_escape 0x10,0xd,0x2,0x76,0x68
	.cfi_escape 0x10,0xc,0x2,0x76,0x60
	pushq	%rbx
	subq	$4096, %rsp
	orq	$0, (%rsp)
	subq	$4096, %rsp
	orq	$0, (%rsp)
	subq	$2368, %rsp
	.cfi_escape 0x10,0x3,0x2,0x76,0x50
	movq	%rdi, -10416(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -56(%rbp)
	xorl	%eax, %eax
	cmpl	$3, (%rsi)
	jle	.L3051
	vmovsd	.LC26(%rip), %xmm1
	movq	2824(%rsi), %rdx
	vxorpd	%xmm7, %xmm7, %xmm7
	movq	%rsi, %r15
	movq	2832(%rsi), %rax
	vmovsd	.LC69(%rip), %xmm2
	subq	%rdx, %rax
	vcvtsi2sdq	%rax, %xmm7, %xmm0
	movabsq	$4700000000, %rax
	vdivsd	%xmm1, %xmm0, %xmm0
	vmulsd	.LC68(%rip), %xmm0, %xmm0
	vcomisd	%xmm0, %xmm2
	ja	.L4034
.L3049:
	addq	%rdx, %rax
	movq	%rax, %rbx
	movq	%rax, -10384(%rbp)
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	cmpq	%rax, %rbx
	jg	.L4035
.L3051:
	movq	-10416(%rbp), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqu	%xmm0, (%rax)
	movq	$0, 16(%rax)
.L3046:
	movq	-56(%rbp), %rax
	subq	%fs:40, %rax
	jne	.L4036
	movq	-10416(%rbp), %rax
	addq	$10560, %rsp
	popq	%rbx
	popq	%r10
	.cfi_remember_state
	.cfi_def_cfa 10, 0
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	leaq	-8(%r10), %rsp
	.cfi_def_cfa 7, 8
	ret
.L4034:
	.cfi_restore_state
	vmulsd	%xmm1, %xmm0, %xmm0
	vcvttsd2siq	%xmm0, %rax
	jmp	.L3049
.L4035:
	movl	12(%r15), %eax
	addl	$2, %eax
	cltq
	movq	%rax, %rcx
	shrq	$58, %rcx
	jne	.L4037
	vpxor	%xmm0, %xmm0, %xmm0
	movq	%rax, %rbx
	movq	$0, -9920(%rbp)
	vmovdqa	%xmm0, -9936(%rbp)
	salq	$5, %rbx
	testq	%rax, %rax
	je	.L3053
	movq	%rbx, %rdi
.LEHB33:
	call	_Znwm@PLT
.LEHE33:
	vpxor	%xmm0, %xmm0, %xmm0
	leaq	(%rax,%rbx), %rdx
	movq	%rax, -9936(%rbp)
	movq	%rdx, -9920(%rbp)
.L3054:
	vmovdqu	%xmm0, (%rax)
	movq	$0, 16(%rax)
	addq	$32, %rax
	cmpq	%rdx, %rax
	jne	.L3054
.L3532:
	cmpl	$21, (%r15)
	leaq	-9936(%rbp), %rax
	movq	%rdx, -9928(%rbp)
	movq	%r15, -10000(%rbp)
	movq	%rax, -10544(%rbp)
	movq	%rax, -9992(%rbp)
	jg	.L3055
	xorl	%ebx, %ebx
	leaq	-10000(%rbp), %r13
	movl	$1, %r12d
	jmp	.L3058
	.p2align 4
	.p2align 3
.L3056:
	movl	(%r15), %eax
	incl	%ebx
	shlx	%eax, %r12d, %eax
	cmpl	%ebx, %eax
	jbe	.L4030
.L3058:
	movl	%ebx, %esi
	movq	%r13, %rdi
.LEHB34:
	call	_ZZN9Optimizer14informed_seedsEvENKUljE_clEj
.LEHE34:
	movl	%ebx, %eax
	andl	$16383, %eax
	cmpl	$16383, %eax
	jne	.L3056
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	addq	$500000000, %rax
	cmpq	%rax, -10384(%rbp)
	jg	.L3056
.L4030:
	vmovss	.LC37(%rip), %xmm7
	vmovss	%xmm7, -10068(%rbp)
.L3057:
	vmovss	-10068(%rbp), %xmm7
	leaq	-9728(%rbp), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, -9888(%rbp)
	movq	%rax, -10536(%rbp)
	movq	%rax, -9776(%rbp)
	movq	-9936(%rbp), %rbx
	vmovdqa	%xmm0, -9904(%rbp)
	movq	$1, -9768(%rbp)
	movq	$0, -9760(%rbp)
	movq	$0, -9752(%rbp)
	movq	$0, -9736(%rbp)
	movq	$0, -9728(%rbp)
	movq	-9928(%rbp), %rax
	vmovss	%xmm7, -9744(%rbp)
	movq	%rax, -10056(%rbp)
	cmpq	%rbx, %rax
	je	.L3275
.L3276:
	vpxor	%xmm5, %xmm5, %xmm5
	movq	$0, -9632(%rbp)
	vmovdqa	%xmm5, -9648(%rbp)
	movq	(%rbx), %r8
	cmpq	8(%rbx), %r8
	je	.L3247
	xorl	%eax, %eax
	xorl	%r12d, %r12d
	leaq	-9648(%rbp), %r14
	jmp	.L3253
.L3250:
	movq	%r13, 8(%rbx)
	cmpq	%r13, %r8
	je	.L3252
.L3251:
	movq	-9632(%rbp), %rax
.L3253:
	cmpq	%rax, %r12
	je	.L3248
	vmovdqu	(%r8), %xmm7
	addq	$16, %r12
	vmovdqu	%xmm7, -16(%r12)
	movq	%r12, -9640(%rbp)
.L3249:
	movq	8(%rbx), %rax
	movq	(%rbx), %r8
	movq	%rax, %rdx
	leaq	-16(%rax), %r13
	subq	%r8, %rdx
	cmpq	$16, %rdx
	jle	.L3250
	vmovdqu	(%r8), %xmm5
	movq	-16(%rax), %rdx
	movq	%r8, %rdi
	xorl	%esi, %esi
	movq	-8(%rax), %rcx
	movq	%r8, -10040(%rbp)
	vmovq	%rdx, %xmm0
	movq	%r13, %rdx
	subq	%r8, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm5, -16(%rax)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	movq	%r13, 8(%rbx)
	movq	-10040(%rbp), %r8
	cmpq	%r13, %r8
	jne	.L3251
.L3252:
	movq	-9648(%rbp), %r14
	cmpq	%r12, %r14
	je	.L3254
	movq	%r12, %r13
	movl	$63, %edx
	movq	%r12, %rsi
	movq	%r14, %rdi
	subq	%r14, %r13
	movq	%r13, %rax
	sarq	$4, %rax
	lzcntq	%rax, %rax
	subl	%eax, %edx
	movslq	%edx, %rdx
	addq	%rdx, %rdx
	call	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElNS0_5__ops15_Iter_less_iterEEvT_SA_T0_T1_.isra.0
	cmpq	$256, %r13
	jle	.L3255
	leaq	256(%r14), %r13
	movq	%r14, %rdi
	movq	%r13, %rsi
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0
	movq	%r13, %rax
	cmpq	%r12, %r13
	je	.L3257
.L3263:
	vmovsd	(%rax), %xmm0
	movq	8(%rax), %rsi
	movq	%rax, %rdx
	jmp	.L3258
.L3259:
	subq	$16, %rdx
	cmpq	-8(%rcx), %rsi
	jnb	.L3262
.L3261:
	vmovdqu	(%rdx), %xmm7
	vmovdqu	%xmm7, 16(%rdx)
.L3258:
	vmovsd	-16(%rdx), %xmm1
	movq	%rdx, %rcx
	vucomisd	%xmm1, %xmm0
	jp	.L3636
	je	.L3259
.L3636:
	subq	$16, %rdx
	vcomisd	%xmm0, %xmm1
	ja	.L3261
.L3262:
	addq	$16, %rax
	vmovsd	%xmm0, (%rcx)
	movq	%rsi, 8(%rcx)
	cmpq	%r12, %rax
	jne	.L3263
.L3257:
	leaq	-9776(%rbp), %rax
	movq	%r14, -10040(%rbp)
	movq	%rax, -10048(%rbp)
.L3273:
	movq	-10040(%rbp), %rax
	xorl	%edx, %edx
	movq	-9768(%rbp), %rsi
	movq	8(%rax), %rax
	movq	%rax, -10088(%rbp)
	movl	%eax, %r8d
	movl	%eax, %eax
	movq	%rax, -10096(%rbp)
	divq	%rsi
	movq	-9776(%rbp), %rax
	movq	(%rax,%rdx,8), %rax
	movq	%rdx, -10080(%rbp)
	testq	%rax, %rax
	je	.L3265
	movq	(%rax), %rcx
	movl	8(%rcx), %edi
.L3267:
	cmpl	%edi, %r8d
	je	.L3515
	movq	(%rcx), %rcx
	testq	%rcx, %rcx
	je	.L3265
	movl	8(%rcx), %eax
	xorl	%edx, %edx
	movq	%rax, %rdi
	divq	%rsi
	cmpq	%rdx, -10080(%rbp)
	je	.L3267
.L3265:
	movl	$16, %edi
	movq	-10048(%rbp), %r13
.LEHB35:
	call	_Znwm@PLT
.LEHE35:
	movq	%rax, %rcx
	movq	$0, (%rax)
	movq	-10048(%rbp), %r13
	movq	%rax, -10064(%rbp)
	movl	$1, %r8d
	movl	-10088(%rbp), %eax
	movq	-10096(%rbp), %rdx
	movq	-10080(%rbp), %rsi
	movq	%r13, %rdi
	movl	%eax, 8(%rcx)
.LEHB36:
	call	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE21_M_insert_unique_nodeEmmPNS1_10_Hash_nodeIjLb0EEEm
.LEHE36:
	movq	-10040(%rbp), %rax
	movq	-9896(%rbp), %rsi
	movq	8(%rax), %rax
	movl	%eax, -9712(%rbp)
	cmpq	-9888(%rbp), %rsi
	je	.L4038
	movl	%eax, (%rsi)
	addq	$4, %rsi
	movq	%rsi, -9896(%rbp)
.L3515:
	addq	$16, -10040(%rbp)
	movq	-10040(%rbp), %rax
	cmpq	%r12, %rax
	jne	.L3273
	movq	-9632(%rbp), %rsi
	subq	%r14, %rsi
	testq	%r14, %r14
	jne	.L4039
.L3247:
	addq	$32, %rbx
	cmpq	%rbx, -10056(%rbp)
	jne	.L3276
.L3275:
	movl	$16, %edi
.LEHB37:
	call	_Znwm@PLT
.LEHE37:
	vpxor	%xmm0, %xmm0, %xmm0
	leaq	16(%rax), %r13
	movl	$16, %edi
	movq	%rax, -10256(%rbp)
	vmovdqu	%xmm0, (%rax)
	movq	%rax, -9872(%rbp)
	movq	%r13, -9856(%rbp)
	movq	%r13, -9864(%rbp)
.LEHB38:
	call	_Znwm@PLT
.LEHE38:
	movslq	4(%r15), %r12
	vpxor	%xmm0, %xmm0, %xmm0
	leaq	16(%rax), %rdx
	movq	%rax, -9840(%rbp)
	vmovdqu	%xmm0, (%rax)
	movq	%rdx, -9824(%rbp)
	movq	%rdx, -9832(%rbp)
	movq	%r12, %rax
	shrq	$61, %rax
	jne	.L4040
	leaq	0(,%r12,4), %rbx
	testq	%r12, %r12
	je	.L3583
	movq	%rbx, %rdi
.LEHB39:
	call	_Znwm@PLT
.LEHE39:
	movq	%rax, %rcx
	movq	%rax, -10128(%rbp)
	leaq	(%rax,%rbx), %rax
	movl	4(%r15), %r14d
	movq	%rax, -10400(%rbp)
	movl	$0, (%rcx)
	leaq	4(%rcx), %rdi
	cmpq	$1, %r12
	je	.L3279
	movq	%rax, %r12
	cmpq	%rdi, %rax
	je	.L3279
	leaq	-4(%rbx), %rdx
	xorl	%esi, %esi
	call	memset@PLT
	movq	%r12, %rdi
.L3279:
	testl	%r14d, %r14d
	jle	.L3278
	leal	-1(%r14), %eax
	cmpl	$14, %eax
	jbe	.L3585
	vmovdqa32	.LC57(%rip), %zmm0
	vpbroadcastd	.LC64(%rip), %zmm1
	movl	%r14d, %edx
	movq	-10128(%rbp), %rax
	shrl	$4, %edx
	decl	%edx
	salq	$6, %rdx
	leaq	64(%rax,%rdx), %rdx
.L3284:
	vmovdqa32	%zmm0, %zmm2
	addq	$64, %rax
	vpaddd	%zmm1, %zmm0, %zmm0
	vmovdqu32	%zmm2, -64(%rax)
	cmpq	%rdx, %rax
	jne	.L3284
	movl	%r14d, %edx
	andl	$-16, %edx
	movl	%edx, %eax
	cmpl	%edx, %r14d
	je	.L4024
.L3283:
	movl	%r14d, %ecx
	subl	%edx, %ecx
	leal	-1(%rcx), %esi
	cmpl	$6, %esi
	jbe	.L3287
	vpbroadcastd	%eax, %ymm0
	vpaddd	.LC48(%rip), %ymm0, %ymm0
	movq	-10128(%rbp), %rsi
	vmovdqu	%ymm0, (%rsi,%rdx,4)
	movl	%ecx, %edx
	andl	$-8, %edx
	addl	%edx, %eax
	cmpl	%edx, %ecx
	je	.L4024
.L3287:
	movq	-10128(%rbp), %rsi
	movslq	%eax, %rdx
	leal	1(%rax), %ecx
	salq	$2, %rdx
	movl	%eax, (%rsi,%rdx)
	cmpl	%r14d, %ecx
	jge	.L4024
	movl	%ecx, 4(%rsi,%rdx)
	leal	2(%rax), %ecx
	cmpl	%r14d, %ecx
	jge	.L4024
	movl	%ecx, 8(%rsi,%rdx)
	leal	3(%rax), %ecx
	cmpl	%r14d, %ecx
	jge	.L4024
	movl	%ecx, 12(%rsi,%rdx)
	leal	4(%rax), %ecx
	cmpl	%r14d, %ecx
	jge	.L4024
	movl	%ecx, 16(%rsi,%rdx)
	leal	5(%rax), %ecx
	cmpl	%r14d, %ecx
	jge	.L4024
	addl	$6, %eax
	movl	%ecx, 20(%rsi,%rdx)
	cmpl	%r14d, %eax
	jge	.L4024
	movl	%eax, 24(%rsi,%rdx)
	vzeroupper
	jmp	.L3278
.L3055:
	movq	56(%r15), %rax
	movq	48(%r15), %rbx
	vpxor	%xmm0, %xmm0, %xmm0
	leaq	-8296(%rbp), %rcx
	vmovdqa	%xmm0, -9776(%rbp)
	movq	$0, -9760(%rbp)
	xorl	%r8d, %r8d
	movq	%rcx, -10048(%rbp)
	movq	%rax, -10040(%rbp)
	cmpq	%rax, %rbx
	je	.L4041
.L3074:
	movl	(%rbx), %eax
	leaq	40(%rbx), %r12
	xorl	%r14d, %r14d
	testl	%eax, %eax
	jle	.L3076
.L3073:
	movl	4(%rbx,%r14,4), %eax
	movl	12(%r15), %esi
	movslq	%r14d, %rdx
	movl	%eax, -8304(%rbp)
	movl	16(%rbx,%r14,4), %eax
	movl	%eax, -8300(%rbp)
	testl	%esi, %esi
	jle	.L3068
	movq	-10048(%rbp), %rcx
	movl	%esi, %edi
	leal	-1(%rsi), %eax
	subq	%r12, %rcx
	cmpq	$48, %rcx
	jbe	.L3064
	cmpl	$2, %eax
	jbe	.L3064
	cmpl	$6, %eax
	jbe	.L3537
	vmovupd	-8(%r12), %zmm7
	movl	%esi, %ecx
	andl	$-8, %ecx
	movl	%ecx, %eax
	vmovupd	%zmm7, -8296(%rbp)
	cmpl	%esi, %ecx
	je	.L3068
	subl	%ecx, %edi
	leal	-1(%rdi), %r9d
	cmpl	$2, %r9d
	jbe	.L3069
.L3065:
	leaq	4(%rcx,%r14,8), %r9
	vmovapd	(%rbx,%r9,8), %ymm7
	vmovupd	%ymm7, -8296(%rbp,%rcx,8)
	movl	%edi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %eax
	cmpl	%edi, %ecx
	je	.L3068
.L3069:
	movslq	%eax, %rcx
	salq	$3, %rdx
	leaq	(%rdx,%rcx), %rdi
	vmovsd	32(%rbx,%rdi,8), %xmm0
	vmovsd	%xmm0, -8296(%rbp,%rcx,8)
	leal	1(%rax), %ecx
	cmpl	%esi, %ecx
	jge	.L3068
	movslq	%ecx, %rcx
	addl	$2, %eax
	leaq	(%rdx,%rcx), %rdi
	vmovsd	32(%rbx,%rdi,8), %xmm0
	vmovsd	%xmm0, -8296(%rbp,%rcx,8)
	cmpl	%esi, %eax
	jge	.L3068
	cltq
	addq	%rax, %rdx
	vmovsd	32(%rbx,%rdx,8), %xmm0
	vmovsd	%xmm0, -8296(%rbp,%rax,8)
.L3068:
	movq	-9768(%rbp), %rax
	cmpq	%r8, %rax
	je	.L4042
	vmovdqa	-8304(%rbp), %xmm7
	addq	$72, %rax
	vmovdqu	%xmm7, -72(%rax)
	vmovdqa	-8288(%rbp), %xmm7
	vmovdqu	%xmm7, -56(%rax)
	vmovdqa	-8272(%rbp), %xmm7
	vmovdqu	%xmm7, -40(%rax)
	vmovdqa	-8256(%rbp), %xmm7
	vmovdqu	%xmm7, -24(%rax)
	movq	-8240(%rbp), %rdx
	movq	%rdx, -8(%rax)
	movq	%rax, -9768(%rbp)
.L3072:
	incq	%r14
	addq	$64, %r12
	cmpl	%r14d, (%rbx)
	jg	.L3073
.L3076:
	addq	$736, %rbx
	cmpq	%rbx, -10040(%rbp)
	jne	.L3074
	movq	-9776(%rbp), %rax
	subq	%rax, %r8
	movq	%rax, -10064(%rbp)
	movq	%r8, -10144(%rbp)
	vzeroupper
.L3060:
	vmovss	.LC37(%rip), %xmm7
	leaq	-9600(%rbp), %rax
	leaq	-9616(%rbp), %rdi
	movl	$100000, %esi
	movq	%rax, -10424(%rbp)
	movq	%rax, -9648(%rbp)
	leaq	-9648(%rbp), %rax
	movq	$1, -9640(%rbp)
	movq	$0, -9632(%rbp)
	movq	$0, -9624(%rbp)
	movq	$0, -9608(%rbp)
	movq	$0, -9600(%rbp)
	movq	$0, -9712(%rbp)
	movq	%rax, -10112(%rbp)
	vmovss	%xmm7, -10068(%rbp)
	vmovss	%xmm7, -9616(%rbp)
.LEHB40:
	call	_ZNKSt8__detail20_Prime_rehash_policy11_M_next_bktEm@PLT
.LEHE40:
	movq	%rax, %rsi
	cmpq	-9640(%rbp), %rax
	jne	.L4043
	leaq	-9648(%rbp), %rax
	movq	$0, -9608(%rbp)
	movq	%rax, -10112(%rbp)
.L3078:
	movq	-9768(%rbp), %rax
	movabsq	$-8198552921648689607, %rdx
	movl	$-1, -10056(%rbp)
	movl	$0, -10048(%rbp)
	subq	-10064(%rbp), %rax
	sarq	$3, %rax
	imulq	%rdx, %rax
	movq	%rax, -10152(%rbp)
.L3079:
	movl	12(%r15), %r13d
	testl	%r13d, %r13d
	jle	.L3085
	movl	-10048(%rbp), %eax
	testl	%eax, %eax
	je	.L3080
	cmpl	%r13d, %eax
	jg	.L4044
	leal	-1(%r13), %edx
	cmpl	$6, %edx
	jbe	.L3538
	decl	%eax
	movl	%r13d, %edx
	vpbroadcastd	%eax, %ymm0
	andl	$-8, %edx
	vpcmpd	$0, .LC48(%rip), %ymm0, %k1
	vbroadcastsd	.LC1(%rip), %ymm0
	vmovapd	%ymm0, %ymm2{%k1}{z}
	kshiftrb	$4, %k1, %k1
	vmovapd	%ymm0, %ymm1{%k1}{z}
	vmovapd	%ymm2, -9584(%rbp)
	vmovapd	%ymm1, -9552(%rbp)
	testb	$7, %r13b
	je	.L3085
.L3087:
	vmovsd	.LC1(%rip), %xmm0
	cmpl	-10056(%rbp), %edx
	je	.L3089
	vxorpd	%xmm0, %xmm0, %xmm0
.L3089:
	movslq	%edx, %rcx
	vmovsd	%xmm0, -9584(%rbp,%rcx,8)
	leal	1(%rdx), %ecx
	cmpl	%r13d, %ecx
	jge	.L3085
	vmovsd	.LC1(%rip), %xmm0
	cmpl	-10056(%rbp), %ecx
	je	.L3090
	vxorpd	%xmm0, %xmm0, %xmm0
.L3090:
	movslq	%ecx, %rcx
	vmovsd	%xmm0, -9584(%rbp,%rcx,8)
	leal	2(%rdx), %ecx
	cmpl	%r13d, %ecx
	jge	.L3085
	vmovsd	.LC1(%rip), %xmm0
	cmpl	-10056(%rbp), %ecx
	je	.L3091
	vxorpd	%xmm0, %xmm0, %xmm0
.L3091:
	movslq	%ecx, %rcx
	vmovsd	%xmm0, -9584(%rbp,%rcx,8)
	leal	3(%rdx), %ecx
	cmpl	%r13d, %ecx
	jge	.L3085
	vmovsd	.LC1(%rip), %xmm0
	cmpl	-10056(%rbp), %ecx
	je	.L3092
	vxorpd	%xmm0, %xmm0, %xmm0
.L3092:
	movslq	%ecx, %rcx
	vmovsd	%xmm0, -9584(%rbp,%rcx,8)
	leal	4(%rdx), %ecx
	cmpl	%r13d, %ecx
	jge	.L3085
	vmovsd	.LC1(%rip), %xmm0
	cmpl	-10056(%rbp), %ecx
	je	.L3093
	vxorpd	%xmm0, %xmm0, %xmm0
.L3093:
	movslq	%ecx, %rcx
	vmovsd	%xmm0, -9584(%rbp,%rcx,8)
	leal	5(%rdx), %ecx
	cmpl	%ecx, %r13d
	jle	.L3085
	vmovsd	.LC1(%rip), %xmm0
	cmpl	%ecx, -10056(%rbp)
	je	.L3094
	vxorpd	%xmm0, %xmm0, %xmm0
.L3094:
	movslq	%ecx, %rcx
	addl	$6, %edx
	vmovsd	%xmm0, -9584(%rbp,%rcx,8)
	cmpl	%edx, %r13d
	jle	.L3085
	vmovsd	.LC1(%rip), %xmm0
	cmpl	%edx, -10056(%rbp)
	je	.L4027
	vxorpd	%xmm0, %xmm0, %xmm0
.L4027:
	movslq	%edx, %rdx
	vmovsd	%xmm0, -9584(%rbp,%rdx,8)
.L3085:
	cmpq	$0, -10152(%rbp)
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, -9696(%rbp)
	vmovdqa	%xmm0, -9712(%rbp)
	je	.L3547
	vxorpd	%xmm7, %xmm7, %xmm7
	movq	-10064(%rbp), %rbx
	movq	$0, -10096(%rbp)
	xorl	%r14d, %r14d
	xorl	%r12d, %r12d
	vmovsd	%xmm7, -10040(%rbp)
	jmp	.L3101
.L3106:
	vxorpd	.LC6(%rip), %xmm1, %xmm1
	movl	%r12d, -9800(%rbp)
	vmovsd	%xmm1, -9808(%rbp)
	cmpq	-10096(%rbp), %r14
	je	.L3109
	vmovdqa	-9808(%rbp), %xmm5
	addq	$16, %r14
	vmovdqu	%xmm5, -16(%r14)
	movq	%r14, -9704(%rbp)
.L3110:
	incq	%r12
	addq	$72, %rbx
	cmpq	-10152(%rbp), %r12
	je	.L3111
	movl	12(%r15), %r13d
.L3101:
	vxorpd	%xmm1, %xmm1, %xmm1
	testl	%r13d, %r13d
	jle	.L3113
	leal	-1(%r13), %edx
	cmpl	$6, %edx
	jbe	.L3548
	vmovupd	8(%rbx), %zmm7
	vmovsd	-10040(%rbp), %xmm3
	movl	%r13d, %ecx
	vmulpd	-9584(%rbp), %zmm7, %zmm0
	andl	$-8, %ecx
	movl	%ecx, %edx
	vunpckhpd	%xmm0, %xmm0, %xmm2
	vextractf64x2	$0x1, %ymm0, %xmm1
	vaddsd	%xmm0, %xmm3, %xmm3
	vextractf64x4	$0x1, %zmm0, %ymm0
	vaddsd	%xmm3, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm1, %xmm2
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm2, %xmm1, %xmm1
	vunpckhpd	%xmm0, %xmm0, %xmm2
	vaddsd	%xmm1, %xmm0, %xmm1
	vextractf64x2	$0x1, %ymm0, %xmm0
	vaddsd	%xmm1, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm0, %xmm1
	vunpckhpd	%xmm0, %xmm0, %xmm0
	vaddsd	%xmm0, %xmm1, %xmm1
	cmpl	%r13d, %ecx
	je	.L3113
.L3102:
	movl	%r13d, %esi
	subl	%ecx, %esi
	leal	-1(%rsi), %edi
	cmpl	$2, %edi
	jbe	.L3104
	movq	-10064(%rbp), %rax
	leaq	(%r12,%r12,8), %rdi
	leaq	1(%rcx,%rdi), %rdi
	vmovupd	(%rax,%rdi,8), %ymm0
	vmulpd	-9584(%rbp,%rcx,8), %ymm0, %ymm0
	movl	%esi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %edx
	vaddsd	%xmm1, %xmm0, %xmm1
	vunpckhpd	%xmm0, %xmm0, %xmm2
	vextractf64x2	$0x1, %ymm0, %xmm0
	vaddsd	%xmm1, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm0, %xmm1
	vunpckhpd	%xmm0, %xmm0, %xmm0
	vaddsd	%xmm0, %xmm1, %xmm1
	cmpl	%esi, %ecx
	je	.L3113
.L3104:
	movslq	%edx, %rcx
	vmovsd	8(%rbx,%rcx,8), %xmm7
	leaq	(%rbx,%rcx,8), %rsi
	vfmadd231sd	-9584(%rbp,%rcx,8), %xmm7, %xmm1
	leal	1(%rdx), %ecx
	cmpl	%r13d, %ecx
	jge	.L3113
	vmovsd	16(%rsi), %xmm7
	movslq	%ecx, %rcx
	addl	$2, %edx
	vfmadd231sd	-9584(%rbp,%rcx,8), %xmm7, %xmm1
	cmpl	%r13d, %edx
	jge	.L3113
	vmovsd	24(%rsi), %xmm7
	movslq	%edx, %rdx
	vfmadd231sd	-9584(%rbp,%rdx,8), %xmm7, %xmm1
.L3113:
	cmpl	%r13d, -10048(%rbp)
	jle	.L3106
	movq	2792(%r15), %rax
	cmpq	$311, %rax
	ja	.L4045
	vzeroupper
.L3107:
	leaq	1(%rax), %rdx
	movq	296(%r15,%rax,8), %rax
	movabsq	$6148914691236517205, %rcx
	vxorpd	%xmm7, %xmm7, %xmm7
	movq	%rdx, 2792(%r15)
	vmovsd	.LC1(%rip), %xmm5
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%rcx, %rdx
	movabsq	$8202884508482404352, %rcx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rcx, %rdx
	movabsq	$-2270628950310912, %rcx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rcx, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	vcvtusi2sdq	%rax, %xmm7, %xmm0
	vaddsd	-10040(%rbp), %xmm0, %xmm0
	vmovsd	.LC70(%rip), %xmm7
	vmulsd	%xmm7, %xmm0, %xmm0
	vcomisd	%xmm5, %xmm0
	jnb	.L3549
	vmovsd	.LC72(%rip), %xmm7
	vfmadd132sd	.LC71(%rip), %xmm7, %xmm0
.L3108:
	vmovsd	%xmm1, -10080(%rbp)
	call	log@PLT
	vmovsd	.LC76(%rip), %xmm2
	vmovsd	-10080(%rbp), %xmm1
	vsubsd	%xmm0, %xmm2, %xmm0
	vdivsd	%xmm0, %xmm1, %xmm1
	jmp	.L3106
.L4042:
	leaq	-9776(%rbp), %r13
	leaq	-8304(%rbp), %rdx
	movq	%r8, %rsi
	movq	%r13, %rdi
	vzeroupper
.LEHB41:
	call	_ZNSt6vectorIZN9Optimizer14informed_seedsEvE10ConstraintSaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
.LEHE41:
	movq	-9760(%rbp), %r8
	jmp	.L3072
.L3537:
	xorl	%eax, %eax
	xorl	%ecx, %ecx
	jmp	.L3065
.L3064:
	vmovsd	-8(%r12), %xmm0
	vmovsd	%xmm0, -8296(%rbp)
	cmpl	$1, %esi
	je	.L3068
	vmovsd	(%r12), %xmm0
	vmovsd	%xmm0, -8288(%rbp)
	cmpl	$2, %esi
	je	.L3068
	vmovsd	8(%r12), %xmm0
	vmovsd	%xmm0, -8280(%rbp)
	cmpl	$3, %esi
	je	.L3068
	vmovsd	16(%r12), %xmm0
	vmovsd	%xmm0, -8272(%rbp)
	cmpl	$4, %esi
	je	.L3068
	vmovsd	24(%r12), %xmm0
	vmovsd	%xmm0, -8264(%rbp)
	cmpl	$5, %esi
	je	.L3068
	vmovsd	32(%r12), %xmm0
	vmovsd	%xmm0, -8256(%rbp)
	cmpl	$6, %esi
	je	.L3068
	vmovsd	40(%r12), %xmm0
	vmovsd	%xmm0, -8248(%rbp)
	cmpl	$7, %esi
	je	.L3068
	vmovsd	48(%r12), %xmm0
	vmovsd	%xmm0, -8240(%rbp)
	jmp	.L3068
.L3248:
	movq	%r8, %rdx
	movq	%r12, %rsi
	movq	%r14, %rdi
	leaq	-9776(%rbp), %r13
.LEHB42:
	call	_ZNSt6vectorI5StateSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
	movq	-9640(%rbp), %r12
	jmp	.L3249
.L3255:
	movq	%r12, %rsi
	movq	%r14, %rdi
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0
	jmp	.L3257
.L3254:
	movq	-9632(%rbp), %rsi
	subq	%r12, %rsi
	testq	%r14, %r14
	je	.L3247
.L4039:
	movq	%r14, %rdi
	addq	$32, %rbx
	call	_ZdlPvm@PLT
	cmpq	%rbx, -10056(%rbp)
	jne	.L3276
	jmp	.L3275
.L4038:
	leaq	-9712(%rbp), %rdx
	leaq	-9904(%rbp), %rdi
	call	_ZNSt6vectorIjSaIjEE17_M_realloc_insertIJjEEEvN9__gnu_cxx17__normal_iteratorIPjS1_EEDpOT_
.LEHE42:
	jmp	.L3515
.L4036:
	call	__stack_chk_fail@PLT
	.p2align 4
	.p2align 3
.L3583:
	xorl	%edi, %edi
	movq	$0, -10128(%rbp)
	movq	$0, -10400(%rbp)
.L3278:
	movq	%rdi, %rsi
	leaq	296(%r15), %rdx
	movq	-10128(%rbp), %rdi
	call	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPiSt6vectorIiSaIiEEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SA_OT0_
	movl	8(%r15), %edx
	movl	$2, %esi
	testl	%edx, %edx
	jle	.L3282
	movl	4(%r15), %ecx
	movl	$1, %r12d
.L3297:
	movl	$1, %eax
	shlx	%r12, %rax, %rbx
	shlx	%rcx, %rax, %rax
	decq	%rbx
	cmpq	%rax, %rbx
	jnb	.L3289
.L3296:
	movq	24(%r15), %rcx
	movq	%rbx, %rax
	xorl	%r14d, %r14d
	xorl	%r13d, %r13d
.L3290:
	movq	-10128(%rbp), %rsi
	tzcntq	%rax, %rdx
	movslq	(%rsi,%rdx,4), %rsi
	xorl	(%rcx,%rsi,4), %r13d
	movq	%rsi, %rdx
	movl	$1, %esi
	shlx	%rdx, %rsi, %rdx
	orq	%rdx, %r14
	blsr	%rax, %rax
	jne	.L3290
	movq	-9832(%rbp), %rsi
	movl	%r13d, -9648(%rbp)
	movq	%r14, -9640(%rbp)
	cmpq	-9824(%rbp), %rsi
	je	.L3291
	vmovdqa	-9648(%rbp), %xmm5
	addq	$16, %rsi
	vmovdqu	%xmm5, -16(%rsi)
	movq	%rsi, -9832(%rbp)
.L3292:
	movl	8(%r15), %edx
	movl	%edx, %eax
	shrl	$31, %eax
	addl	%edx, %eax
	sarl	%eax
	cmpl	%r12d, %eax
	jge	.L4046
.L3293:
	blsi	%rbx, %rcx
	xorl	%edx, %edx
	leaq	(%rcx,%rbx), %rsi
	xorq	%rsi, %rbx
	shrq	$2, %rbx
	movq	%rbx, %rax
	divq	%rcx
	movl	4(%r15), %ecx
	movq	%rax, %rbx
	movl	$1, %eax
	orq	%rsi, %rbx
	shlx	%rcx, %rax, %rax
	cmpq	%rbx, %rax
	ja	.L3296
	movl	8(%r15), %edx
.L3289:
	leal	1(%rdx), %esi
	incl	%r12d
	movl	%esi, %eax
	shrl	$31, %eax
	addl	%esi, %eax
	sarl	%eax
	cmpl	%r12d, %eax
	jge	.L3297
	movq	-9864(%rbp), %r13
	movq	-9872(%rbp), %rax
	vxorpd	%xmm5, %xmm5, %xmm5
	movq	%r13, %rcx
	movq	%rax, -10256(%rbp)
	subq	%rax, %rcx
	movq	%rcx, %rax
	sarq	$4, %rax
	addq	%rax, %rax
	vcvtusi2sdq	%rax, %xmm5, %xmm0
	movl	$1, %eax
	vcvttsd2usi	%xmm0, %rsi
	testq	%rsi, %rsi
	cmove	%rax, %rsi
.L3282:
	vmovss	-10068(%rbp), %xmm7
	leaq	-9680(%rbp), %r14
	leaq	-9664(%rbp), %rax
	movq	$1, -9704(%rbp)
	movq	%r14, %rdi
	movq	%rax, -10480(%rbp)
	movq	%rax, -9712(%rbp)
	movq	$0, -9696(%rbp)
	movq	$0, -9688(%rbp)
	movq	$0, -9672(%rbp)
	movq	$0, -9664(%rbp)
	movq	$0, -9648(%rbp)
	vmovss	%xmm7, -9680(%rbp)
.LEHB43:
	call	_ZNKSt8__detail20_Prime_rehash_policy11_M_next_bktEm@PLT
	movq	%rax, %rsi
	cmpq	-9704(%rbp), %rax
	je	.L3298
	leaq	-9648(%rbp), %rax
	leaq	-9712(%rbp), %rdi
	movq	%rax, %rdx
	call	_ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm
.L3299:
	movq	-10256(%rbp), %rax
	cmpq	%rax, %r13
	je	.L3300
	movq	%rax, %rbx
	leaq	-9648(%rbp), %rax
	movq	%rax, -10048(%rbp)
.L3306:
	movl	$24, %edi
	call	_Znwm@PLT
.LEHE43:
	movq	8(%rbx), %rdx
	movq	%rax, %r12
	movq	$0, (%rax)
	movl	(%rbx), %eax
	movq	-9704(%rbp), %rsi
	movl	$1, %ecx
	movq	%r14, %rdi
	movl	%eax, 8(%r12)
	movq	%rdx, 16(%r12)
	movq	%rax, -10040(%rbp)
	movq	-9688(%rbp), %rdx
	movq	-9672(%rbp), %rax
	movq	%rax, -9648(%rbp)
.LEHB44:
	call	_ZNKSt8__detail20_Prime_rehash_policy14_M_need_rehashEmmm@PLT
.LEHE44:
	movq	%rdx, %rsi
	testb	%al, %al
	jne	.L4047
.L3301:
	movq	-9704(%rbp), %rcx
	movq	-10040(%rbp), %rax
	xorl	%edx, %edx
	movq	-9712(%rbp), %r8
	divq	%rcx
	leaq	(%r8,%rdx,8), %rdi
	movq	%rdx, %r11
	movq	(%rdi), %rsi
	testq	%rsi, %rsi
	je	.L3302
	vmovd	8(%r12), %xmm0
	movq	(%rsi), %r8
	movl	8(%r8), %r9d
	movq	%r8, %rax
	vmovd	%xmm0, %edx
	cmpl	%r9d, %edx
	je	.L3303
.L4048:
	movq	(%rax), %r10
	testq	%r10, %r10
	je	.L3304
	movl	8(%r10), %r9d
	movq	%rax, %rsi
	xorl	%edx, %edx
	movl	%r9d, %eax
	divq	%rcx
	cmpq	%rdx, %r11
	jne	.L3304
	vmovd	%xmm0, %edx
	movq	%r10, %rax
	cmpl	%r9d, %edx
	jne	.L4048
.L3303:
	movq	%rax, (%r12)
	movq	%r12, (%rsi)
	jmp	.L3516
.L4040:
	leaq	.LC11(%rip), %rdi
.LEHB45:
	call	_ZSt20__throw_length_errorPKc@PLT
.LEHE45:
	.p2align 4
	.p2align 3
.L3548:
	xorl	%ecx, %ecx
	xorl	%edx, %edx
	vxorpd	%xmm1, %xmm1, %xmm1
	jmp	.L3102
.L3547:
	movq	$0, -10096(%rbp)
	xorl	%r14d, %r14d
.L3100:
	xorl	%eax, %eax
	leaq	-9328(%rbp), %rdi
	movl	$14, %ecx
	leaq	-8304(%rbp), %rsi
	movq	%rdi, -10088(%rbp)
	movq	%r14, %r13
	xorl	%r12d, %r12d
	xorl	%ebx, %ebx
	rep stosq
	leaq	-8816(%rbp), %rdi
	movl	$14, %ecx
	movq	%rdi, -10136(%rbp)
	rep stosq
	movl	$14, %ecx
	movq	%rsi, %rdi
	rep stosq
	movslq	(%r15), %rax
.L3126:
	testl	%eax, %eax
	jle	.L3128
	xorl	%edx, %edx
	movl	$1, %edi
	movq	%rax, %r9
.L3130:
	movq	-10136(%rbp), %rax
	movq	-10088(%rbp), %r11
	movl	(%rax,%rdx,4), %ecx
	shlx	%edx, %edi, %eax
	andn	(%r11,%rdx,4), %eax, %eax
	movl	%ecx, (%rsi,%rdx,4)
	testl	%eax, %eax
	je	.L3132
.L3129:
	tzcntl	%eax, %r8d
	xorl	-8304(%rbp,%r8,4), %ecx
	blsr	%eax, %eax
	movl	%ecx, (%rsi,%rdx,4)
	jne	.L3129
.L3132:
	incq	%rdx
	cmpq	%r9, %rdx
	jne	.L3130
	vmovdqa	.LC48(%rip), %ymm7
	vpbroadcastd	.LC80(%rip), %ymm6
	leaq	-9456(%rbp), %rdi
	xorl	%eax, %eax
	movl	$14, %ecx
	movq	%rdi, -10088(%rbp)
	vmovq	%r9, %xmm1
	movl	$0, -9904(%rbp)
	xorl	%edx, %edx
	xorl	%r9d, %r9d
	xorl	%r8d, %r8d
	vpxor	%xmm5, %xmm5, %xmm5
	rep stosq
	leal	-1(%r12), %eax
	movl	%r12d, %edi
	vpxor	%xmm4, %xmm4, %xmm4
	vmovq	%rsi, %xmm2
	vmovd	%eax, %xmm8
	movl	%r12d, %eax
	andl	$-16, %edi
	shrl	$4, %eax
	movl	%eax, -10040(%rbp)
.L3151:
	vmovq	%xmm2, %rax
	movl	%edx, %r10d
	movl	(%rax,%rdx,4), %ecx
	movl	%ecx, %eax
	andl	%ebx, %eax
	popcntl	%eax, %eax
	testb	$1, %al
	je	.L3133
	movl	$1, %eax
	movl	$1, %r9d
	shlx	%edx, %eax, %eax
	orl	%eax, %r8d
.L3133:
	testl	%r12d, %r12d
	jle	.L3154
	movl	$1, %eax
	shlx	%r10d, %eax, %r10d
	vmovd	%xmm8, %eax
	cmpl	$14, %eax
	jbe	.L3552
	vpbroadcastd	%ecx, %zmm11
	vpsrlvd	.LC57(%rip), %zmm11, %zmm0
	vpandd	.LC77(%rip), %zmm0, %zmm0
	vpbroadcastd	%r10d, %zmm10
	vpcmpd	$4, %zmm4, %zmm0, %k1
	kortestw	%k1, %k1
	jne	.L4049
.L3135:
	cmpl	$1, -10040(%rbp)
	jbe	.L3136
	vmovdqa32	.LC67(%rip), %zmm9
	leaq	-9392(%rbp), %rax
	movl	$1, %r11d
	vmovq	%xmm2, %rsi
	jmp	.L3138
.L3137:
	incl	%r11d
	addq	$64, %rax
	cmpl	-10040(%rbp), %r11d
	je	.L4050
.L3138:
	vmovdqa32	%zmm9, %zmm0
	vpaddd	.LC60(%rip), %zmm9, %zmm9
	vpsrlvd	%zmm0, %zmm11, %zmm0
	vpandd	.LC77(%rip), %zmm0, %zmm0
	vpcmpd	$4, %zmm4, %zmm0, %k1
	kortestw	%k1, %k1
	je	.L3137
	vmovdqa32	-10352(%rbp), %zmm3
	incl	%r11d
	vmovdqa32	(%rax), %zmm3{%k1}
	vpord	%zmm3, %zmm10, %zmm0
	vmovdqa32	%zmm3, -10352(%rbp)
	vmovdqa32	%zmm0, (%rax){%k1}
	addq	$64, %rax
	cmpl	-10040(%rbp), %r11d
	jne	.L3138
.L4050:
	vmovq	%rsi, %xmm2
.L3136:
	cmpl	%r12d, %edi
	je	.L3154
	movl	%edi, %r11d
	movl	%edi, %eax
.L3134:
	movl	%r12d, %r14d
	subl	%r11d, %r14d
	leal	-1(%r14), %esi
	cmpl	$6, %esi
	jbe	.L3140
	vpbroadcastd	%eax, %ymm10
	movq	-10088(%rbp), %rsi
	vpbroadcastd	%ecx, %ymm0
	vpbroadcastd	%r10d, %ymm9
	vpaddd	%ymm7, %ymm10, %ymm10
	vpsrlvd	%ymm10, %ymm0, %ymm0
	vpand	%ymm6, %ymm0, %ymm0
	vpcmpd	$4, %ymm5, %ymm0, %k1
	kortestb	%k1, %k1
	leaq	(%rsi,%r11,4), %r11
	jne	.L4051
.L3141:
	movl	%r14d, %r11d
	andl	$-8, %r11d
	addl	%r11d, %eax
	cmpl	%r14d, %r11d
	je	.L3154
.L3140:
	btl	%eax, %ecx
	jnc	.L3143
	movslq	%eax, %r11
	orl	%r10d, -9456(%rbp,%r11,4)
.L3143:
	leal	1(%rax), %r11d
	cmpl	%r11d, %r12d
	jle	.L3154
	btl	%r11d, %ecx
	jnc	.L3144
	movslq	%r11d, %r11
	orl	%r10d, -9456(%rbp,%r11,4)
.L3144:
	leal	2(%rax), %r11d
	cmpl	%r11d, %r12d
	jle	.L3154
	btl	%r11d, %ecx
	jnc	.L3145
	movslq	%r11d, %r11
	orl	%r10d, -9456(%rbp,%r11,4)
.L3145:
	leal	3(%rax), %r11d
	cmpl	%r11d, %r12d
	jle	.L3154
	btl	%r11d, %ecx
	jnc	.L3146
	movslq	%r11d, %r11
	orl	%r10d, -9456(%rbp,%r11,4)
.L3146:
	leal	4(%rax), %r11d
	cmpl	%r11d, %r12d
	jle	.L3154
	btl	%r11d, %ecx
	jnc	.L3147
	movslq	%r11d, %r11
	orl	%r10d, -9456(%rbp,%r11,4)
.L3147:
	leal	5(%rax), %r11d
	cmpl	%r11d, %r12d
	jle	.L3154
	btl	%r11d, %ecx
	jnc	.L3148
	movslq	%r11d, %r11
	orl	%r10d, -9456(%rbp,%r11,4)
.L3148:
	addl	$6, %eax
	cmpl	%eax, %r12d
	jle	.L3154
	btl	%eax, %ecx
	jnc	.L3154
	cltq
	orl	%r10d, -9456(%rbp,%rax,4)
.L3154:
	incq	%rdx
	vmovq	%xmm1, %rax
	cmpq	%rdx, %rax
	jne	.L3151
	testb	%r9b, %r9b
	je	.L3155
	movl	%r8d, -9904(%rbp)
.L3155:
	movq	-10112(%rbp), %rdi
	leaq	-9904(%rbp), %rsi
	vzeroupper
.LEHB46:
	call	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKjNS1_10_AllocNodeISaINS1_10_Hash_nodeIjLb0EEEEEEEESt4pairINS1_14_Node_iteratorIjLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
	testb	%dl, %dl
	jne	.L4052
.L3156:
	testl	%r12d, %r12d
	jle	.L3232
	movl	-9904(%rbp), %eax
	movq	$0, -10136(%rbp)
	movl	%eax, -10240(%rbp)
	leal	-1(%r12), %eax
	movq	%rax, -10160(%rbp)
	movq	-10088(%rbp), %rax
	movq	%rax, -10104(%rbp)
	leaq	-9872(%rbp), %rax
	movq	%rax, -10368(%rbp)
.L3233:
	movq	-10104(%rbp), %rcx
	movl	-10240(%rbp), %eax
	movq	-10368(%rbp), %rsi
	movq	-10112(%rbp), %rdi
	xorl	(%rcx), %eax
	movl	%eax, -9872(%rbp)
	call	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKjNS1_10_AllocNodeISaINS1_10_Hash_nodeIjLb0EEEEEEEESt4pairINS1_14_Node_iteratorIjLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
	testb	%dl, %dl
	jne	.L4053
.L3157:
	movq	-10136(%rbp), %rcx
	cmpq	%rcx, -10160(%rbp)
	je	.L3232
.L4063:
	movl	-9872(%rbp), %eax
	movl	%eax, -10248(%rbp)
	leal	-2(%r12), %eax
	subl	%ecx, %eax
	addq	%rcx, %rax
	movq	-10088(%rbp), %rcx
	leaq	4(%rcx,%rax,4), %rax
	movq	%rax, -10232(%rbp)
	movq	-10104(%rbp), %rax
	movq	%rax, -10080(%rbp)
	leaq	-9840(%rbp), %rax
	movq	%rax, -10376(%rbp)
	jmp	.L3230
.L3194:
	addq	$4, -10080(%rbp)
	movq	-10080(%rbp), %rax
	cmpq	-10232(%rbp), %rax
	je	.L4054
.L3230:
	movq	-10080(%rbp), %rcx
	movl	-10248(%rbp), %eax
	movq	-10376(%rbp), %rsi
	movq	-10112(%rbp), %rdi
	xorl	4(%rcx), %eax
	movl	%eax, -9840(%rbp)
	call	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKjNS1_10_AllocNodeISaINS1_10_Hash_nodeIjLb0EEEEEEEESt4pairINS1_14_Node_iteratorIjLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
	testb	%dl, %dl
	je	.L3194
	movl	-9840(%rbp), %esi
	movq	-10000(%rbp), %r14
	movl	%esi, -10128(%rbp)
	movl	2800(%r14), %ecx
	movl	%esi, %eax
	cmpl	%ecx, (%r14)
	jle	.L3195
	imull	$-1640531535, %esi, %eax
	movl	$32, %edx
	subl	%ecx, %edx
	shrx	%edx, %eax, %eax
.L3195:
	movq	72(%r14), %rdx
	movl	-10128(%rbp), %edi
	leaq	(%rdx,%rax,4), %rdx
	salq	$6, %rax
	addq	96(%r14), %rax
	cmpl	(%rdx), %edi
	je	.L3196
	movq	48(%r14), %rcx
	movq	56(%r14), %r8
	incq	2816(%r14)
	vbroadcastsd	.LC1(%rip), %zmm0
	movl	%edi, (%rdx)
	cmpq	%r8, %rcx
	je	.L3197
.L3198:
	movl	(%rcx), %r9d
	xorl	%edx, %edx
	testl	%r9d, %r9d
	jle	.L3201
	movl	4(%rcx), %edx
	andl	%edi, %edx
	popcntl	%edx, %edx
	andl	$1, %edx
	cmpl	$1, %r9d
	je	.L3201
	movl	8(%rcx), %esi
	andl	%edi, %esi
	popcntl	%esi, %esi
	andl	$1, %esi
	addl	%esi, %esi
	orl	%esi, %edx
	cmpl	$2, %r9d
	je	.L3201
	movl	12(%rcx), %esi
	andl	%edi, %esi
	popcntl	%esi, %esi
	andl	$1, %esi
	sall	$2, %esi
	orl	%esi, %edx
.L3201:
	movslq	%edx, %rdx
	addq	$736, %rcx
	salq	$6, %rdx
	vmulpd	-512(%rcx,%rdx), %zmm0, %zmm0
	cmpq	%rcx, %r8
	jne	.L3198
.L3197:
	vmovupd	%zmm0, (%rax)
	vzeroupper
.L3196:
	movl	12(%r14), %edx
	testl	%edx, %edx
	jle	.L3202
	vmovsd	(%rax), %xmm3
	vxorpd	%xmm5, %xmm5, %xmm5
	vminsd	.LC1(%rip), %xmm3, %xmm2
	vmaxsd	.LC3(%rip), %xmm3, %xmm1
	vaddsd	%xmm5, %xmm3, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9504(%rbp)
	cmpl	$1, %edx
	je	.L3205
	vmovsd	8(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9496(%rbp)
	cmpl	$2, %edx
	je	.L3205
	vmovsd	16(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9488(%rbp)
	cmpl	$3, %edx
	je	.L3205
	vmovsd	24(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9480(%rbp)
	cmpl	$4, %edx
	je	.L3205
	vmovsd	32(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9472(%rbp)
	cmpl	$5, %edx
	je	.L3205
	vmovsd	40(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9464(%rbp)
.L3205:
	vxorpd	.LC6(%rip), %xmm1, %xmm4
	vxorpd	%xmm7, %xmm7, %xmm7
	vandpd	.LC5(%rip), %xmm0, %xmm0
	vxorpd	.LC6(%rip), %xmm2, %xmm3
	vxorpd	.LC6(%rip), %xmm0, %xmm0
	vcmpnltsd	%xmm4, %xmm2, %xmm2
	vblendvpd	%xmm2, %xmm3, %xmm1, %xmm1
	vcvtsi2sdl	%edx, %xmm7, %xmm2
	vdivsd	%xmm2, %xmm0, %xmm0
	vunpcklpd	%xmm0, %xmm1, %xmm1
	vmovapd	%xmm1, -9520(%rbp)
.L3217:
	movq	-9992(%rbp), %rax
	movq	$0, -10040(%rbp)
	leaq	-9520(%rbp), %rbx
	movq	%rax, -10256(%rbp)
	leaq	-9808(%rbp), %rax
	movq	%rax, -10392(%rbp)
.L3228:
	movq	-10040(%rbp), %rsi
	movq	-10256(%rbp), %rcx
	movq	%rsi, %rax
	salq	$5, %rax
	addq	(%rcx), %rax
	movq	(%rax), %rcx
	movq	%rax, -10120(%rbp)
	movq	8(%rax), %rax
	movq	%rax, -10360(%rbp)
	subq	%rcx, %rax
	cmpq	$752, %rax
	jbe	.L3218
	vmovsd	(%rbx,%rsi,8), %xmm0
	vcomisd	(%rcx), %xmm0
	jnb	.L3219
.L3218:
	movq	-10040(%rbp), %rax
	movq	-10392(%rbp), %rsi
	movq	-10120(%rbp), %rdi
	vmovsd	(%rbx,%rax,8), %xmm0
	movl	-10128(%rbp), %eax
	movq	%rax, -9800(%rbp)
	vmovsd	%xmm0, -9808(%rbp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	-10120(%rbp), %rax
	movq	8(%rax), %r9
	movq	(%rax), %rdi
	movq	%r9, %r8
	vmovsd	-16(%r9), %xmm1
	movq	-8(%r9), %r10
	subq	%rdi, %r8
	movq	%r8, %rdx
	sarq	$4, %rdx
	leaq	-1(%rdx), %rax
	subq	$2, %rdx
	movq	%rdx, %rsi
	shrq	$63, %rsi
	addq	%rdx, %rsi
	sarq	%rsi
	testq	%rax, %rax
	jg	.L3224
	jmp	.L4055
.L3221:
	cmpq	%r10, 8(%rcx)
	setb	%dl
.L3223:
	salq	$4, %rax
	addq	%rdi, %rax
	testb	%dl, %dl
	je	.L3225
	vmovdqu	(%rcx), %xmm7
	vmovdqu	%xmm7, (%rax)
	leaq	-1(%rsi), %rax
	movq	%rax, %rdx
	shrq	$63, %rdx
	addq	%rax, %rdx
	movq	%rsi, %rax
	sarq	%rdx
	testq	%rsi, %rsi
	jle	.L4056
	movq	%rdx, %rsi
.L3224:
	movq	%rsi, %rcx
	salq	$4, %rcx
	addq	%rdi, %rcx
	vmovsd	(%rcx), %xmm0
	vucomisd	%xmm1, %xmm0
	jp	.L3635
	je	.L3221
.L3635:
	vcomisd	%xmm0, %xmm1
	seta	%dl
	jmp	.L3223
.L3111:
	movq	-9712(%rbp), %r13
	cmpq	%r14, %r13
	je	.L3100
	movq	%r14, %rbx
	movl	$63, %edx
	movq	%r14, %rsi
	movq	%r13, %rdi
	subq	%r13, %rbx
	movq	%rbx, %rax
	sarq	$4, %rax
	lzcntq	%rax, %rax
	subl	%eax, %edx
	movslq	%edx, %rdx
	addq	%rdx, %rdx
	call	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEElNS0_5__ops15_Iter_less_iterEEvT_SB_T0_T1_.isra.0
	cmpq	$256, %rbx
	jle	.L3114
	leaq	256(%r13), %rbx
	movq	%r13, %rdi
	movq	%rbx, %rsi
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_less_iterEEvT_SB_T0_.isra.0
	movq	%rbx, %rax
	cmpq	%r14, %rbx
	jne	.L3121
	jmp	.L3116
	.p2align 4
	.p2align 3
.L4057:
	vcomisd	%xmm1, %xmm0
	ja	.L3119
	movl	-8(%rdx), %ecx
	cmpl	%ecx, %esi
	jl	.L3120
.L3119:
	addq	$16, %rax
	vmovsd	%xmm0, (%rdx)
	movl	%esi, 8(%rdx)
	cmpq	%rax, %r14
	je	.L3116
.L3121:
	vmovsd	(%rax), %xmm0
	movl	8(%rax), %esi
	movq	%rax, %rdx
.L3117:
	vmovsd	-16(%rdx), %xmm1
	vcomisd	%xmm0, %xmm1
	jbe	.L4057
	movl	-8(%rdx), %ecx
.L3120:
	vmovsd	%xmm1, (%rdx)
	movl	%ecx, 8(%rdx)
	subq	$16, %rdx
	jmp	.L3117
.L3114:
	movq	%r14, %rsi
	movq	%r13, %rdi
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIPSt4pairIdiESt6vectorIS3_SaIS3_EEEENS0_5__ops15_Iter_less_iterEEvT_SB_T0_.isra.0
.L3116:
	xorl	%eax, %eax
	leaq	-9328(%rbp), %rdi
	movl	$14, %ecx
	movq	%rdi, -10088(%rbp)
	leaq	-8304(%rbp), %rsi
	xorl	%r12d, %r12d
	xorl	%ebx, %ebx
	rep stosq
	leaq	-8816(%rbp), %rdi
	movl	$14, %ecx
	movq	%rdi, -10136(%rbp)
	rep stosq
	movl	$14, %ecx
	movq	%rsi, %rdi
	rep stosq
	movslq	(%r15), %rax
	movl	$1, %ecx
	movq	%r13, %rdi
	vmovd	%ecx, %xmm0
	movl	$31, %ecx
	vmovd	%ecx, %xmm7
.L3127:
	movslq	8(%rdi), %rdx
	movq	-10064(%rbp), %rcx
	leaq	(%rdx,%rdx,8), %rdx
	leaq	(%rcx,%rdx,8), %r11
	vmovd	%xmm0, %edx
	movl	(%r11), %ecx
	shlx	%r12d, %edx, %r9d
	testl	%ecx, %ecx
	je	.L3123
	movq	%r14, %rdx
	movl	%r12d, %r14d
	movq	%rdx, %r12
	jmp	.L3125
.L4059:
	movl	%r10d, %r8d
	xorl	-8816(%rbp,%rdx,4), %r9d
	xorl	%ecx, %r8d
	vmovd	%r8d, %xmm1
	cmpl	%ecx, %r10d
	je	.L4058
	vmovd	%xmm1, %ecx
.L3125:
	lzcntl	%ecx, %r10d
	vmovd	%xmm7, %edx
	subl	%r10d, %edx
	movslq	%edx, %rdx
	movl	-9328(%rbp,%rdx,4), %r10d
	testl	%r10d, %r10d
	jne	.L4059
	movl	%ecx, -9328(%rbp,%rdx,4)
	movl	%r9d, -8816(%rbp,%rdx,4)
	movl	4(%r11), %edx
	movq	%r12, %r10
	movl	%r14d, %r12d
	movq	%r10, %r14
	shlx	%r12d, %edx, %edx
	incl	%r12d
	orl	%edx, %ebx
	jmp	.L3123
.L3109:
	leaq	-9808(%rbp), %rdx
	leaq	-9712(%rbp), %rdi
	movq	%r14, %rsi
	vzeroupper
	call	_ZNSt6vectorISt4pairIdiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movq	-9696(%rbp), %rax
	movq	-9704(%rbp), %r14
	movq	%rax, -10096(%rbp)
	jmp	.L3110
.L4056:
	movq	%rcx, %rax
.L3225:
	vmovsd	%xmm1, (%rax)
	movq	%r10, 8(%rax)
	cmpq	$768, %r8
	ja	.L3226
.L4029:
	movl	12(%r14), %edx
.L3219:
	incq	-10040(%rbp)
	movq	-10040(%rbp), %rax
	decl	%eax
	cmpl	%edx, %eax
	jle	.L3228
	jmp	.L3194
.L3226:
	leaq	-16(%r9), %rax
	cmpq	$16, %r8
	jg	.L4060
.L3227:
	movq	-10120(%rbp), %rcx
	movq	%rax, 8(%rcx)
	jmp	.L4029
.L4060:
	vmovdqu	(%rdi), %xmm5
	movq	-16(%r9), %rdx
	xorl	%esi, %esi
	movq	%rax, -10360(%rbp)
	movq	-8(%r9), %rcx
	vmovq	%rdx, %xmm0
	movq	%rax, %rdx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm5, -16(%r9)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	movq	-10360(%rbp), %rax
	jmp	.L3227
.L4055:
	leaq	-16(%rdi,%r8), %rax
	jmp	.L3225
.L3202:
	vxorpd	%xmm7, %xmm7, %xmm7
	vcvtsi2sdl	%edx, %xmm7, %xmm0
	vmovsd	.LC7(%rip), %xmm7
	vdivsd	%xmm0, %xmm7, %xmm0
	vmovsd	.LC3(%rip), %xmm7
	vunpcklpd	%xmm0, %xmm7, %xmm0
	vmovapd	%xmm0, -9520(%rbp)
	cmpl	$-1, %edx
	jl	.L3194
	jmp	.L3217
.L4053:
	movl	-9872(%rbp), %esi
	movq	-10000(%rbp), %r14
	movl	%esi, -10120(%rbp)
	movl	2800(%r14), %ecx
	movl	%esi, %eax
	cmpl	%ecx, (%r14)
	jle	.L3158
	imull	$-1640531535, %esi, %eax
	movl	$32, %edx
	subl	%ecx, %edx
	shrx	%edx, %eax, %eax
.L3158:
	movq	72(%r14), %rdx
	movl	-10120(%rbp), %edi
	leaq	(%rdx,%rax,4), %rdx
	salq	$6, %rax
	addq	96(%r14), %rax
	cmpl	(%rdx), %edi
	je	.L3159
	movq	48(%r14), %rcx
	movq	56(%r14), %r8
	incq	2816(%r14)
	vbroadcastsd	.LC1(%rip), %zmm0
	movl	%edi, (%rdx)
	cmpq	%r8, %rcx
	je	.L3160
.L3161:
	movl	(%rcx), %r9d
	xorl	%edx, %edx
	testl	%r9d, %r9d
	jle	.L3164
	movl	4(%rcx), %edx
	andl	%edi, %edx
	popcntl	%edx, %edx
	andl	$1, %edx
	cmpl	$1, %r9d
	je	.L3164
	movl	8(%rcx), %esi
	andl	%edi, %esi
	popcntl	%esi, %esi
	andl	$1, %esi
	addl	%esi, %esi
	orl	%esi, %edx
	cmpl	$2, %r9d
	je	.L3164
	movl	12(%rcx), %esi
	andl	%edi, %esi
	popcntl	%esi, %esi
	andl	$1, %esi
	sall	$2, %esi
	orl	%esi, %edx
.L3164:
	movslq	%edx, %rdx
	addq	$736, %rcx
	salq	$6, %rdx
	vmulpd	-512(%rcx,%rdx), %zmm0, %zmm0
	cmpq	%rcx, %r8
	jne	.L3161
.L3160:
	vmovupd	%zmm0, (%rax)
	vzeroupper
.L3159:
	movl	12(%r14), %edx
	testl	%edx, %edx
	jle	.L3165
	vmovsd	(%rax), %xmm3
	vxorpd	%xmm7, %xmm7, %xmm7
	vminsd	.LC1(%rip), %xmm3, %xmm2
	vmaxsd	.LC3(%rip), %xmm3, %xmm1
	vaddsd	%xmm7, %xmm3, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9504(%rbp)
	cmpl	$1, %edx
	je	.L3168
	vmovsd	8(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9496(%rbp)
	cmpl	$2, %edx
	je	.L3168
	vmovsd	16(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9488(%rbp)
	cmpl	$3, %edx
	je	.L3168
	vmovsd	24(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9480(%rbp)
	cmpl	$4, %edx
	je	.L3168
	vmovsd	32(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9472(%rbp)
	cmpl	$5, %edx
	je	.L3168
	vmovsd	40(%rax), %xmm3
	vminsd	%xmm2, %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vandpd	.LC5(%rip), %xmm3, %xmm3
	vxorpd	.LC6(%rip), %xmm3, %xmm3
	vmovsd	%xmm3, -9464(%rbp)
.L3168:
	vxorpd	.LC6(%rip), %xmm1, %xmm4
	vxorpd	%xmm5, %xmm5, %xmm5
	vandpd	.LC5(%rip), %xmm0, %xmm0
	vxorpd	.LC6(%rip), %xmm2, %xmm3
	vxorpd	.LC6(%rip), %xmm0, %xmm0
	vcmpnltsd	%xmm4, %xmm2, %xmm2
	vblendvpd	%xmm2, %xmm3, %xmm1, %xmm1
	vcvtsi2sdl	%edx, %xmm5, %xmm2
	vdivsd	%xmm2, %xmm0, %xmm0
	vunpcklpd	%xmm0, %xmm1, %xmm1
	vmovapd	%xmm1, -9520(%rbp)
.L3180:
	movq	-9992(%rbp), %rax
	movq	$0, -10040(%rbp)
	leaq	-9520(%rbp), %rbx
	movq	%rax, -10128(%rbp)
	leaq	-9840(%rbp), %rax
	movq	%rax, -10248(%rbp)
.L3191:
	movq	-10040(%rbp), %rsi
	movq	-10128(%rbp), %rcx
	movq	%rsi, %rax
	salq	$5, %rax
	addq	(%rcx), %rax
	movq	(%rax), %rcx
	movq	%rax, -10080(%rbp)
	movq	8(%rax), %rax
	movq	%rax, -10232(%rbp)
	subq	%rcx, %rax
	cmpq	$752, %rax
	jbe	.L3181
	vmovsd	(%rbx,%rsi,8), %xmm0
	vcomisd	(%rcx), %xmm0
	jnb	.L3182
.L3181:
	movq	-10040(%rbp), %rax
	movq	-10248(%rbp), %rsi
	movq	-10080(%rbp), %rdi
	vmovsd	(%rbx,%rax,8), %xmm0
	movl	-10120(%rbp), %eax
	movq	%rax, -9832(%rbp)
	vmovsd	%xmm0, -9840(%rbp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	-10080(%rbp), %rax
	movq	8(%rax), %r8
	movq	(%rax), %rdi
	movq	%r8, %rsi
	vmovsd	-16(%r8), %xmm0
	movq	-8(%r8), %r10
	subq	%rdi, %rsi
	movq	%rsi, %rdx
	sarq	$4, %rdx
	leaq	-1(%rdx), %rax
	subq	$2, %rdx
	movq	%rdx, %rcx
	shrq	$63, %rcx
	addq	%rdx, %rcx
	sarq	%rcx
	testq	%rax, %rax
	jg	.L3187
	jmp	.L4061
.L3184:
	cmpq	8(%r9), %r10
	seta	%dl
.L3186:
	salq	$4, %rax
	addq	%rdi, %rax
	testb	%dl, %dl
	je	.L3188
	vmovdqu	(%r9), %xmm5
	vmovdqu	%xmm5, (%rax)
	leaq	-1(%rcx), %rax
	movq	%rax, %rdx
	shrq	$63, %rdx
	addq	%rax, %rdx
	movq	%rcx, %rax
	sarq	%rdx
	testq	%rcx, %rcx
	jle	.L4062
	movq	%rdx, %rcx
.L3187:
	movq	%rcx, %r9
	salq	$4, %r9
	addq	%rdi, %r9
	vmovsd	(%r9), %xmm1
	vucomisd	%xmm1, %xmm0
	jp	.L3634
	je	.L3184
.L3634:
	vcomisd	%xmm1, %xmm0
	seta	%dl
	jmp	.L3186
.L4062:
	movq	%r9, %rax
.L3188:
	vmovsd	%xmm0, (%rax)
	movq	%r10, 8(%rax)
	cmpq	$768, %rsi
	ja	.L3189
.L4028:
	movl	12(%r14), %edx
.L3182:
	incq	-10040(%rbp)
	movq	-10040(%rbp), %rax
	decl	%eax
	cmpl	%edx, %eax
	jle	.L3191
	movq	-10136(%rbp), %rcx
	cmpq	%rcx, -10160(%rbp)
	jne	.L4063
.L3232:
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	movq	-10096(%rbp), %rsi
	addq	$700000000, %rax
	subq	%r13, %rsi
	cmpq	%rax, -10384(%rbp)
	jle	.L3234
	testq	%r13, %r13
	je	.L3235
	movq	%r13, %rdi
	call	_ZdlPvm@PLT
.L3235:
	incl	-10048(%rbp)
	incl	-10056(%rbp)
	movl	-10048(%rbp), %eax
	cmpl	$256, %eax
	jne	.L3079
.L3237:
	movq	-9632(%rbp), %rbx
	testq	%rbx, %rbx
	je	.L3243
.L3240:
	movq	%rbx, %rdi
	movq	(%rbx), %rbx
	movl	$16, %esi
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L3240
.L3243:
	movq	-9640(%rbp), %rax
	movq	-9648(%rbp), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	-9640(%rbp), %rsi
	movq	$0, -9624(%rbp)
	movq	$0, -9632(%rbp)
	movq	-9648(%rbp), %rdi
	cmpq	-10424(%rbp), %rdi
	je	.L3241
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L3241:
	movq	-10064(%rbp), %rax
	testq	%rax, %rax
	je	.L3057
	movq	-10144(%rbp), %rsi
	movq	%rax, %rdi
	call	_ZdlPvm@PLT
	jmp	.L3057
	.p2align 4
	.p2align 3
.L4061:
	leaq	-16(%rdi,%rsi), %rax
	jmp	.L3188
.L3189:
	leaq	-16(%r8), %rax
	cmpq	$16, %rsi
	jg	.L4064
.L3190:
	movq	-10080(%rbp), %rcx
	movq	%rax, 8(%rcx)
	jmp	.L4028
.L3165:
	vmovsd	.LC7(%rip), %xmm1
	vxorpd	%xmm5, %xmm5, %xmm5
	vmovsd	.LC3(%rip), %xmm7
	vcvtsi2sdl	%edx, %xmm5, %xmm0
	vdivsd	%xmm0, %xmm1, %xmm0
	vunpcklpd	%xmm0, %xmm7, %xmm0
	vmovapd	%xmm0, -9520(%rbp)
	cmpl	$-1, %edx
	jl	.L3157
	jmp	.L3180
.L4052:
	movl	-9904(%rbp), %esi
	leaq	-10000(%rbp), %rdi
	call	_ZZN9Optimizer14informed_seedsEvENKUljE_clEj
.LEHE46:
	jmp	.L3156
	.p2align 4
	.p2align 3
.L4054:
	incq	-10136(%rbp)
	addq	$4, -10104(%rbp)
	jmp	.L3233
.L3234:
	testq	%r13, %r13
	je	.L3237
	movq	%r13, %rdi
	call	_ZdlPvm@PLT
	jmp	.L3237
	.p2align 4
	.p2align 3
.L4064:
	vmovdqu	(%rdi), %xmm7
	movq	-16(%r8), %rdx
	xorl	%esi, %esi
	movq	%rax, -10232(%rbp)
	movq	-8(%r8), %rcx
	vmovq	%rdx, %xmm0
	movq	%rax, %rdx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm7, -16(%r8)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	movq	-10232(%rbp), %rax
	jmp	.L3190
.L3552:
	xorl	%r11d, %r11d
	xorl	%eax, %eax
	jmp	.L3134
.L3549:
	vmovsd	.LC66(%rip), %xmm0
	jmp	.L3108
.L4045:
	leaq	296(%r15), %rdi
	vmovsd	%xmm1, -10080(%rbp)
	vzeroupper
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	vmovsd	-10080(%rbp), %xmm1
	movq	2792(%r15), %rax
	jmp	.L3107
.L4049:
	vmovdqa32	-10224(%rbp), %zmm3
	vmovdqa32	-9456(%rbp), %zmm3{%k1}
	vpord	%zmm3, %zmm10, %zmm0
	vmovdqa32	%zmm3, -10224(%rbp)
	vmovdqa32	%zmm0, -9456(%rbp){%k1}
	jmp	.L3135
.L4051:
	vmovdqa	-10288(%rbp), %ymm3
	vmovdqa32	(%r11), %ymm3{%k1}
	vpor	%ymm3, %ymm9, %ymm0
	vmovdqa	%ymm3, -10288(%rbp)
	vmovdqa32	%ymm0, (%r11){%k1}
	jmp	.L3141
.L4046:
	movq	-9864(%rbp), %rsi
	movl	%r13d, -9648(%rbp)
	movq	%r14, -9640(%rbp)
	cmpq	-9856(%rbp), %rsi
	je	.L3294
	vmovdqa	-9648(%rbp), %xmm7
	addq	$16, %rsi
	vmovdqu	%xmm7, -16(%rsi)
	movq	%rsi, -9864(%rbp)
	jmp	.L3293
.L3291:
	leaq	-9648(%rbp), %rax
	leaq	-9840(%rbp), %rdi
	movq	%rax, %rdx
.LEHB47:
	call	_ZNSt6vectorISt4pairIjmESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
.LEHE47:
	jmp	.L3292
.L4043:
	leaq	-9648(%rbp), %rax
	leaq	-9712(%rbp), %rdx
	movq	%rax, %rdi
	movq	%rax, -10112(%rbp)
.LEHB48:
	call	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm
.LEHE48:
	jmp	.L3078
.L3304:
	movq	%r8, (%r12)
	movq	(%rdi), %rax
	movq	%r12, (%rax)
.L3516:
	addq	$16, %rbx
	incq	-9688(%rbp)
	cmpq	%rbx, %r13
	jne	.L3306
.L3300:
	movq	-9904(%rbp), %rax
	movq	-9896(%rbp), %rcx
	movq	%rax, -10440(%rbp)
	subq	%rax, %rcx
	movq	%rcx, %rax
	movq	%rcx, -10392(%rbp)
	sarq	$2, %rax
	movq	%rax, -10360(%rbp)
	movabsq	$9223372036854775804, %rax
	cmpq	%rax, %rcx
	ja	.L4065
	cmpq	$0, -10360(%rbp)
	je	.L3586
	movq	%rcx, %rdi
	movq	%rcx, %rbx
.LEHB49:
	call	_Znwm@PLT
.LEHE49:
	movq	%rax, -10152(%rbp)
	testq	%rbx, %rbx
	je	.L3310
	movq	%rbx, %rdx
	xorl	%esi, %esi
	movq	%rax, %rdi
	call	memset@PLT
.L3310:
	vmovss	-10068(%rbp), %xmm5
	movq	-9840(%rbp), %rsi
	leaq	-9600(%rbp), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movq	-9832(%rbp), %rcx
	movq	%rax, -10424(%rbp)
	movq	%rax, -9648(%rbp)
	movq	$1, -9640(%rbp)
	movq	$0, -9632(%rbp)
	movq	$0, -9624(%rbp)
	movq	$0, -9608(%rbp)
	movq	$0, -9600(%rbp)
	vmovdqa	%xmm0, -9808(%rbp)
	movq	$0, -9792(%rbp)
	movq	%rsi, -10488(%rbp)
	movq	%rsi, -10408(%rbp)
	movq	$0, -10240(%rbp)
	subq	%rsi, %rcx
	movq	%rcx, %rax
	sarq	$4, %rax
	vmovss	%xmm5, -9616(%rbp)
	movq	%rax, -10528(%rbp)
	je	.L4066
.L3456:
	cmpb	$0, 2840(%r15)
	jne	.L3459
	cmpq	$0, -10360(%rbp)
	movq	$0, -10288(%rbp)
	jne	.L3454
	jmp	.L3460
	.p2align 4
	.p2align 3
.L3313:
	incq	-10288(%rbp)
	movq	-10288(%rbp), %rax
	cmpq	-10360(%rbp), %rax
	je	.L3460
.L3454:
	movq	-10152(%rbp), %rcx
	movq	-10288(%rbp), %rax
	cmpl	$31, (%rcx,%rax,4)
	jg	.L3313
	movq	-10440(%rbp), %rcx
	movq	-9704(%rbp), %rsi
	xorl	%edx, %edx
	movl	(%rcx,%rax,4), %ecx
	movq	-10408(%rbp), %rax
	xorl	(%rax), %ecx
	movl	%ecx, %eax
	divq	%rsi
	movq	-9712(%rbp), %rax
	movq	(%rax,%rdx,8), %rax
	movq	%rdx, %r8
	testq	%rax, %rax
	je	.L3313
	movq	(%rax), %r9
	movl	8(%r9), %edi
	cmpl	%edi, %ecx
	je	.L3314
.L4067:
	movq	(%r9), %r9
	testq	%r9, %r9
	je	.L3313
	movl	8(%r9), %eax
	xorl	%edx, %edx
	movq	%rax, %rdi
	divq	%rsi
	cmpq	%rdx, %r8
	jne	.L3313
	cmpl	%edi, %ecx
	jne	.L4067
.L3314:
	movq	(%r9), %rax
	movq	%r9, -10160(%rbp)
	movq	%rax, -10352(%rbp)
	testq	%rax, %rax
	je	.L3318
	movl	8(%r9), %eax
	movq	-10352(%rbp), %rdx
.L3317:
	cmpl	8(%rdx), %eax
	je	.L4068
	movq	%rdx, -10352(%rbp)
	cmpq	%rdx, -10160(%rbp)
	je	.L3313
.L3318:
	movl	$0, -10376(%rbp)
	jmp	.L3450
.L3452:
	movq	-10160(%rbp), %rax
	incl	-10376(%rbp)
	movq	(%rax), %rcx
	movl	-10376(%rbp), %eax
	movq	%rcx, -10160(%rbp)
	cmpl	$128, %eax
	je	.L3313
	cmpq	%rcx, -10352(%rbp)
	je	.L3313
.L3450:
	movq	-10408(%rbp), %rax
	movq	-10160(%rbp), %rcx
	movq	8(%rax), %rax
	movq	16(%rcx), %rdx
	testq	%rdx, %rax
	jne	.L3452
	orq	%rdx, %rax
	leaq	-10024(%rbp), %rsi
	movq	%rax, -10024(%rbp)
	leaq	-9648(%rbp), %rax
	movq	%rax, %rdi
	movq	%rax, -10112(%rbp)
.LEHB50:
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
.LEHE50:
	movb	%dl, -10068(%rbp)
	testb	%dl, %dl
	je	.L3452
	movq	-10152(%rbp), %rax
	movq	-10288(%rbp), %rcx
	movq	-10024(%rbp), %rsi
	incl	(%rax,%rcx,4)
	movl	8(%r15), %eax
	popcntq	%rsi, %rcx
	movq	%rsi, -10224(%rbp)
	movl	%ecx, %edx
	movq	%rsi, -10448(%rbp)
	cmpl	%ecx, %eax
	jle	.L3321
.L3320:
	cmpb	$0, 2840(%r15)
	jne	.L3452
	movl	4(%r15), %ecx
	testl	%ecx, %ecx
	jle	.L3452
	vmovsd	.LC1(%rip), %xmm7
	movq	$0, -10224(%rbp)
	movl	$0, -10248(%rbp)
	vmovsd	%xmm7, -10232(%rbp)
	vmovsd	%xmm7, -10432(%rbp)
.L3449:
	movq	-10448(%rbp), %rax
	movl	-10248(%rbp), %esi
	btq	%rsi, %rax
	jc	.L3322
	movq	128(%r15), %r8
	btsq	%rsi, %rax
	xorl	%edx, %edx
	movq	%rax, -10368(%rbp)
	movq	%rax, -10016(%rbp)
	divq	%r8
	movq	120(%r15), %rax
	movq	(%rax,%rdx,8), %rax
	movq	%rdx, %r9
	testq	%rax, %rax
	je	.L3323
	movq	(%rax), %rsi
	movq	8(%rsi), %rdi
.L3325:
	cmpq	%rdi, -10368(%rbp)
	je	.L3324
	movq	(%rsi), %rsi
	testq	%rsi, %rsi
	je	.L3323
	movq	8(%rsi), %rdi
	xorl	%edx, %edx
	movq	%rdi, %rax
	divq	%r8
	cmpq	%rdx, %r9
	je	.L3325
.L3323:
	movq	2808(%r15), %rax
	incq	%rax
	movq	%rax, 2808(%r15)
	testb	%al, %al
	je	.L4069
.L3327:
	leaq	-8816(%rbp), %rax
	movl	$512, %edx
	xorl	%esi, %esi
	movq	%rax, %rdi
	movq	%rax, -10136(%rbp)
	call	memset@PLT
	movl	$1, %r8d
	leaq	-8812(%rbp), %r10
	movq	24(%r15), %r11
	movq	-10368(%rbp), %r9
	jmp	.L3335
.L4071:
	vpbroadcastd	%edx, %zmm0
	vpxord	-8816(%rbp), %zmm0, %zmm1
	movq	-10136(%rbp), %rax
	movl	%r8d, %esi
	movslq	%r8d, %rcx
	shrl	$4, %esi
	leaq	(%rax,%rcx,4), %rax
	vmovdqu32	%zmm1, (%rax)
	cmpl	$1, %esi
	je	.L3329
	vpxord	-8752(%rbp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 64(%rax)
	cmpl	$2, %esi
	je	.L3329
	vpxord	-8688(%rbp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 128(%rax)
	cmpl	$3, %esi
	je	.L3329
	vpxord	-8624(%rbp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 192(%rax)
	cmpl	$4, %esi
	je	.L3329
	vpxord	-8560(%rbp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 256(%rax)
	cmpl	$5, %esi
	je	.L3329
	vpxord	-8496(%rbp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 320(%rax)
	cmpl	$6, %esi
	je	.L3329
	vpxord	-8432(%rbp), %zmm0, %zmm0
	vmovdqu32	%zmm0, 384(%rax)
.L3329:
	movl	%r8d, %eax
	andl	$-16, %eax
	testb	$15, %r8b
	je	.L3334
	movl	%r8d, %esi
	subl	%eax, %esi
	leal	-1(%rsi), %edi
	cmpl	$6, %edi
	jbe	.L3331
	movl	%eax, %edi
	vpbroadcastd	%edx, %ymm0
	vpxor	-8816(%rbp,%rdi,4), %ymm0, %ymm0
	addq	%rdi, %rcx
	vmovdqu	%ymm0, -8816(%rbp,%rcx,4)
	movl	%esi, %ecx
	andl	$-8, %ecx
	addl	%ecx, %eax
	cmpl	%esi, %ecx
	je	.L3334
.L3331:
	movslq	%eax, %rsi
	leal	(%r8,%rax), %ecx
	movl	-8816(%rbp,%rsi,4), %ebx
	movslq	%ecx, %rcx
	xorl	%edx, %ebx
	movl	%ebx, -8816(%rbp,%rcx,4)
	leal	1(%rax), %ecx
	cmpl	%r8d, %ecx
	jge	.L3334
	leal	(%rcx,%r8), %esi
	movslq	%ecx, %rcx
	movl	-8816(%rbp,%rcx,4), %ebx
	movslq	%esi, %rsi
	leal	2(%rax), %ecx
	xorl	%edx, %ebx
	movl	%ebx, -8816(%rbp,%rsi,4)
	cmpl	%r8d, %ecx
	jge	.L3334
	leal	(%rcx,%r8), %esi
	movslq	%ecx, %rcx
	movl	-8816(%rbp,%rcx,4), %ebx
	movslq	%esi, %rsi
	leal	3(%rax), %ecx
	xorl	%edx, %ebx
	movl	%ebx, -8816(%rbp,%rsi,4)
	cmpl	%ecx, %r8d
	jle	.L3334
	leal	(%r8,%rcx), %esi
	movslq	%ecx, %rcx
	movl	-8816(%rbp,%rcx,4), %ebx
	movslq	%esi, %rsi
	leal	4(%rax), %ecx
	xorl	%edx, %ebx
	movl	%ebx, -8816(%rbp,%rsi,4)
	cmpl	%ecx, %r8d
	jle	.L3334
	leal	(%r8,%rcx), %esi
	movslq	%ecx, %rcx
	movl	-8816(%rbp,%rcx,4), %ebx
	movslq	%esi, %rsi
	leal	5(%rax), %ecx
	xorl	%edx, %ebx
	movl	%ebx, -8816(%rbp,%rsi,4)
	cmpl	%r8d, %ecx
	jge	.L3334
	leal	(%rcx,%r8), %esi
	movslq	%ecx, %rcx
	addl	$6, %eax
	movl	-8816(%rbp,%rcx,4), %ebx
	movslq	%esi, %rsi
	xorl	%edx, %ebx
	movl	%ebx, -8816(%rbp,%rsi,4)
	cmpl	%eax, %r8d
	jle	.L3334
	leal	(%r8,%rax), %ecx
	cltq
	xorl	-8816(%rbp,%rax,4), %edx
	movslq	%ecx, %rcx
	movl	%edx, -8816(%rbp,%rcx,4)
.L3334:
	blsr	%r9, %r9
	leal	(%r8,%r8), %edi
	je	.L4070
.L3588:
	movl	%edi, %r8d
.L3335:
	tzcntq	%r9, %rax
	leal	-1(%r8), %ecx
	movl	(%r11,%rax,4), %edx
	cmpl	$14, %ecx
	ja	.L4071
	movq	-10136(%rbp), %rax
	leaq	(%r10,%rcx,4), %rdi
	movslq	%r8d, %rcx
.L3333:
	movl	(%rax), %esi
	xorl	%edx, %esi
	movl	%esi, (%rax,%rcx,4)
	addq	$4, %rax
	cmpq	%rdi, %rax
	jne	.L3333
	blsr	%r9, %r9
	leal	(%r8,%r8), %edi
	jne	.L3588
.L4070:
	vmovq	72(%r15), %xmm3
	vmovq	96(%r15), %xmm2
	leal	-1(%rdi), %r13d
	leaq	-8304(%rbp), %r12
	movq	%r13, %rax
	movq	-10136(%rbp), %r11
	movq	%r12, -10096(%rbp)
	salq	$6, %rax
	leaq	-8240(%rbp,%rax), %r14
	movl	$32, %eax
	vmovd	%eax, %xmm1
.L3343:
	movl	(%r11), %r10d
	movl	2800(%r15), %eax
	movl	%r10d, %ebx
	cmpl	%eax, (%r15)
	jle	.L3336
	imull	$-1640531535, %r10d, %ebx
	vmovd	%xmm1, %edx
	subl	%eax, %edx
	shrx	%edx, %ebx, %ebx
.L3336:
	vmovq	%xmm3, %rax
	vmovq	%xmm2, %rcx
	leaq	(%rax,%rbx,4), %rax
	salq	$6, %rbx
	addq	%rcx, %rbx
	cmpl	(%rax), %r10d
	je	.L3337
	movq	48(%r15), %rdx
	movq	56(%r15), %rsi
	incq	2816(%r15)
	vbroadcastsd	.LC1(%rip), %zmm0
	movl	%r10d, (%rax)
	cmpq	%rsi, %rdx
	je	.L3338
.L3339:
	movl	(%rdx), %r9d
	xorl	%eax, %eax
	testl	%r9d, %r9d
	jle	.L3342
	movl	4(%rdx), %eax
	andl	%r10d, %eax
	popcntl	%eax, %eax
	andl	$1, %eax
	cmpl	$1, %r9d
	je	.L3342
	movl	8(%rdx), %ecx
	andl	%r10d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	addl	%ecx, %ecx
	orl	%ecx, %eax
	cmpl	$2, %r9d
	je	.L3342
	movl	12(%rdx), %ecx
	andl	%r10d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	sall	$2, %ecx
	orl	%ecx, %eax
.L3342:
	cltq
	addq	$736, %rdx
	salq	$6, %rax
	vmulpd	-512(%rdx,%rax), %zmm0, %zmm0
	cmpq	%rdx, %rsi
	jne	.L3339
.L3338:
	vmovupd	%zmm0, (%rbx)
.L3337:
	vmovdqa	(%rbx), %xmm7
	addq	$64, %r12
	addq	$4, %r11
	vmovdqa	16(%rbx), %xmm5
	vmovdqa	%xmm7, -64(%r12)
	vmovdqa	32(%rbx), %xmm7
	vmovdqa	%xmm5, -48(%r12)
	vmovdqa	48(%rbx), %xmm5
	vmovdqa	%xmm7, -32(%r12)
	vmovdqa	%xmm5, -16(%r12)
	cmpq	%r14, %r12
	jne	.L3343
	movl	$1, %ebx
.L3344:
	movq	-10096(%rbp), %rdx
	movslq	%ebx, %rsi
	xorl	%r9d, %r9d
	addl	%ebx, %ebx
	movq	%rsi, %r10
	salq	$6, %rsi
	.p2align 4
	.p2align 3
.L3348:
	leaq	(%rdx,%rsi), %rcx
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L3345:
	vmovapd	(%rdx,%rax), %zmm0
	vmovapd	(%rcx,%rax), %zmm1
	vaddpd	%zmm1, %zmm0, %zmm2
	vsubpd	%zmm1, %zmm0, %zmm0
	vmovapd	%zmm2, (%rdx,%rax)
	vmovapd	%zmm0, (%rcx,%rax)
	addq	$64, %rax
	cmpq	%rsi, %rax
	jne	.L3345
	addl	%ebx, %r9d
	leaq	(%rcx,%rax), %rdx
	cmpl	%r9d, %edi
	jg	.L3348
	cmpl	%r10d, %r8d
	jg	.L3344
	vmovsd	-10232(%rbp), %xmm5
	vxorpd	%xmm7, %xmm7, %xmm7
	movq	-10096(%rbp), %rax
	vcvtsi2sdl	%edi, %xmm7, %xmm0
	vdivsd	%xmm0, %xmm5, %xmm0
	vbroadcastsd	%xmm0, %zmm0
.L3349:
	vmulpd	(%rax), %zmm0, %zmm1
	addq	$64, %rax
	vmovapd	%zmm1, -64(%rax)
	cmpq	%rax, %r14
	jne	.L3349
	movl	12(%r15), %r12d
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqa	%xmm0, -9584(%rbp)
	vmovdqa	%xmm0, -9568(%rbp)
	vmovdqa	%xmm0, -9552(%rbp)
	vmovdqa	%xmm0, -9536(%rbp)
	testl	%r12d, %r12d
	jle	.L4072
	vmovsd	-10232(%rbp), %xmm7
	vxorpd	%xmm5, %xmm5, %xmm5
	leal	-1(%r12), %eax
	vcvtsi2sdl	%r12d, %xmm5, %xmm0
	movl	%eax, -10104(%rbp)
	vdivsd	%xmm0, %xmm7, %xmm0
	cmpl	$6, %eax
	jbe	.L3591
	movl	%r12d, %edx
	vbroadcastsd	%xmm0, %zmm1
	andl	$-8, %edx
	vmovapd	%zmm1, -9584(%rbp)
	movl	%edx, %eax
	cmpl	%edx, %r12d
	je	.L3354
.L3352:
	movl	%r12d, %ecx
	subl	%edx, %ecx
	leal	-1(%rcx), %esi
	cmpl	$2, %esi
	jbe	.L3355
	vbroadcastsd	%xmm0, %ymm1
	vmovapd	%ymm1, -9584(%rbp,%rdx,8)
	movl	%ecx, %edx
	andl	$-4, %edx
	addl	%edx, %eax
	cmpl	%edx, %ecx
	je	.L3354
.L3355:
	movslq	%eax, %rdx
	vmovsd	%xmm0, -9584(%rbp,%rdx,8)
	leal	1(%rax), %edx
	cmpl	%edx, %r12d
	jle	.L3354
	movslq	%edx, %rdx
	addl	$2, %eax
	vmovsd	%xmm0, -9584(%rbp,%rdx,8)
	cmpl	%eax, %r12d
	jle	.L3354
	cltq
	vmovsd	%xmm0, -9584(%rbp,%rax,8)
.L3354:
	xorl	%eax, %eax
	testl	%r12d, %r12d
	vmovsd	-10232(%rbp), %xmm7
	movslq	%edi, %rdi
	setle	%al
	vmovsd	.LC47(%rip), %xmm5
	movq	%r15, -10552(%rbp)
	leaq	-9520(%rbp), %rbx
	leal	-1(%rax,%rax), %eax
	movq	%r14, %r15
	movl	$2, -10468(%rbp)
	movl	%r12d, %r14d
	movl	%eax, -10472(%rbp)
	movslq	%r12d, %rax
	salq	$3, %rax
	movq	%rax, -10504(%rbp)
	leaq	-9520(%rbp,%rax), %rax
	movq	%rax, -10464(%rbp)
	leaq	0(,%rdi,4), %rax
	movq	%rax, -10496(%rbp)
	movl	%r12d, %eax
	andl	$-8, %eax
	testl	%r12d, %r12d
	vmovsd	%xmm7, -10456(%rbp)
	vmovsd	%xmm7, -10144(%rbp)
	movl	%eax, -10072(%rbp)
	leaq	-9328(%rbp), %rax
	vxorpd	%xmm7, %xmm7, %xmm7
	movq	%rax, -10088(%rbp)
	leaq	-9324(%rbp,%r13,4), %rax
	vmovsd	%xmm7, -10040(%rbp)
	vmovsd	.LC3(%rip), %xmm7
	movq	%rax, -10520(%rbp)
	movl	$1, %eax
	cmovg	%r12d, %eax
	movl	%eax, -10508(%rbp)
	andl	$-8, %eax
	testl	%r12d, %r12d
	movl	%eax, -10512(%rbp)
	movl	-10104(%rbp), %eax
	leaq	8(,%rax,8), %r13
	movl	$8, %eax
	cmovg	%r13, %rax
	movq	%rax, -10080(%rbp)
.L3351:
	testl	%r14d, %r14d
	jle	.L3415
	cmpl	$6, -10104(%rbp)
	jbe	.L3592
	vmovapd	.LC45(%rip), %zmm4
	movl	-10072(%rbp), %eax
	movl	%eax, %edx
	vmovapd	%zmm4, -9520(%rbp)
	cmpl	%eax, %r14d
	je	.L3415
.L3357:
	movl	%r14d, %ecx
	subl	%edx, %ecx
	leal	-1(%rcx), %esi
	cmpl	$2, %esi
	jbe	.L3359
	vmovapd	.LC46(%rip), %ymm6
	vmovapd	%ymm6, -9520(%rbp,%rdx,8)
	movl	%ecx, %edx
	andl	$-4, %edx
	addl	%edx, %eax
	cmpl	%ecx, %edx
	je	.L3415
.L3359:
	movq	.LC43(%rip), %rcx
	movslq	%eax, %rdx
	movq	%rcx, -9520(%rbp,%rdx,8)
	leal	1(%rax), %edx
	cmpl	%edx, %r14d
	jle	.L3415
	movslq	%edx, %rdx
	addl	$2, %eax
	movq	%rcx, -9520(%rbp,%rdx,8)
	cmpl	%eax, %r14d
	jle	.L3415
	cltq
	movq	%rcx, -9520(%rbp,%rax,8)
.L3415:
	movq	-10096(%rbp), %rdi
	xorl	%r10d, %r10d
	movq	%r15, -10048(%rbp)
	movq	%rbx, %r13
	movq	%r10, %r15
	movq	-10088(%rbp), %rax
	movl	-10472(%rbp), %r12d
	movl	-10508(%rbp), %r9d
	movl	-10512(%rbp), %esi
	movl	-10072(%rbp), %r8d
	movq	-10520(%rbp), %r11
	movq	%rdi, %r10
	jmp	.L3361
.L3525:
	movq	.LC43(%rip), %rcx
	movl	$1, (%rax)
	vmovq	%rcx, %xmm0
	cmpl	$7, %r14d
	jle	.L3594
.L4075:
	vmovapd	-9520(%rbp), %zmm6
	vbroadcastsd	%xmm0, %zmm1
	vfnmadd132pd	(%r10), %zmm6, %zmm1
	vmovapd	%zmm1, -9520(%rbp)
	cmpl	%esi, %r9d
	je	.L3369
	movl	%esi, %edx
	movl	%esi, %ecx
.L3367:
	movl	%r9d, %edi
	subl	%edx, %edi
	leal	-1(%rdi), %ebx
	cmpl	$2, %ebx
	jbe	.L3370
	salq	$3, %rdx
	vbroadcastsd	%xmm0, %ymm1
	leaq	0(%r13,%rdx), %rbx
	vmovapd	(%rbx), %ymm4
	vfnmadd132pd	(%r10,%rdx), %ymm4, %ymm1
	movl	%edi, %edx
	andl	$-4, %edx
	addl	%edx, %ecx
	vmovapd	%ymm1, (%rbx)
	cmpl	%edx, %edi
	je	.L3369
.L3370:
	movslq	%ecx, %rdx
	leaq	(%r10,%rdx,8), %rdi
	vmovsd	(%rdi), %xmm1
	vfnmadd213sd	-9520(%rbp,%rdx,8), %xmm0, %xmm1
	vmovsd	%xmm1, -9520(%rbp,%rdx,8)
	leal	1(%rcx), %edx
	cmpl	%edx, %r14d
	jle	.L3369
	movslq	%edx, %rdx
	vmovsd	8(%rdi), %xmm1
	addl	$2, %ecx
	vfnmadd213sd	-9520(%rbp,%rdx,8), %xmm0, %xmm1
	vmovsd	%xmm1, -9520(%rbp,%rdx,8)
	cmpl	%ecx, %r14d
	jle	.L3369
	movslq	%ecx, %rcx
	vmovsd	-9520(%rbp,%rcx,8), %xmm6
	vfnmadd132sd	16(%rdi), %xmm6, %xmm0
	vmovsd	%xmm0, -9520(%rbp,%rcx,8)
.L3369:
	addq	$4, %rax
	addq	$64, %r10
	addq	$8, %r15
	cmpq	%r11, %rax
	je	.L4073
.L3361:
	testl	%r14d, %r14d
	jle	.L4074
	cmpl	$6, -10104(%rbp)
	jbe	.L3593
	vmovapd	-9584(%rbp), %zmm4
	vmovsd	-10040(%rbp), %xmm6
	vmulpd	(%r10), %zmm4, %zmm1
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vextractf64x2	$0x1, %ymm1, %xmm0
	vaddsd	%xmm1, %xmm6, %xmm6
	vextractf64x4	$0x1, %zmm1, %ymm1
	vaddsd	%xmm6, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm0, %xmm2
	vunpckhpd	%xmm0, %xmm0, %xmm0
	vaddsd	%xmm2, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vaddsd	%xmm1, %xmm0, %xmm0
	vextractf64x2	$0x1, %ymm1, %xmm1
	vaddsd	%xmm0, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm1, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm1, %xmm0, %xmm0
	cmpl	%r8d, %r14d
	je	.L3363
	movl	%r8d, %edi
	movl	%r8d, %edx
.L3362:
	movl	%r14d, %ecx
	subl	%edi, %ecx
	leal	-1(%rcx), %ebx
	cmpl	$2, %ebx
	jbe	.L3364
	leaq	(%rdi,%r15), %rbx
	vmovapd	-8304(%rbp,%rbx,8), %ymm1
	vmulpd	-9584(%rbp,%rdi,8), %ymm1, %ymm1
	movl	%ecx, %edi
	andl	$-4, %edi
	addl	%edi, %edx
	vaddsd	%xmm1, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vextractf64x2	$0x1, %ymm1, %xmm1
	vaddsd	%xmm2, %xmm0, %xmm0
	vaddsd	%xmm1, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm1, %xmm0, %xmm0
	cmpl	%edi, %ecx
	je	.L3363
.L3364:
	movslq	%edx, %rcx
	vmovsd	-9584(%rbp,%rcx,8), %xmm4
	leaq	(%r10,%rcx,8), %rdi
	leal	1(%rdx), %ecx
	vfmadd231sd	(%rdi), %xmm4, %xmm0
	cmpl	%ecx, %r14d
	jle	.L3363
	vmovsd	8(%rdi), %xmm6
	movslq	%ecx, %rcx
	addl	$2, %edx
	vfmadd231sd	-9584(%rbp,%rcx,8), %xmm6, %xmm0
	cmpl	%edx, %r14d
	jle	.L3363
	vmovsd	16(%rdi), %xmm4
	movslq	%edx, %rdx
	vfmadd231sd	-9584(%rbp,%rdx,8), %xmm4, %xmm0
.L3363:
	vcomisd	-10040(%rbp), %xmm0
	jnb	.L3525
	vxorpd	%xmm4, %xmm4, %xmm4
	movl	%r12d, (%rax)
	vcvtsi2sdl	%r12d, %xmm4, %xmm0
	vmulsd	.LC43(%rip), %xmm0, %xmm0
	cmpl	$7, %r14d
	jg	.L4075
.L3594:
	xorl	%edx, %edx
	xorl	%ecx, %ecx
	jmp	.L3367
.L3586:
	movq	$0, -10152(%rbp)
	jmp	.L3310
.L4065:
	leaq	.LC11(%rip), %rdi
.LEHB51:
	call	_ZSt20__throw_length_errorPKc@PLT
.LEHE51:
	.p2align 4
	.p2align 3
.L3302:
	movq	-9696(%rbp), %rax
	movq	%r12, -9696(%rbp)
	movq	%rax, (%r12)
	testq	%rax, %rax
	je	.L3528
	movl	8(%rax), %eax
	xorl	%edx, %edx
	divq	%rcx
	movq	%r12, (%r8,%rdx,8)
.L3528:
	leaq	-9696(%rbp), %rax
	movq	%rax, (%rdi)
	jmp	.L3516
.L4047:
	movq	-10048(%rbp), %rdx
	leaq	-9712(%rbp), %rdi
.LEHB52:
	call	_ZNSt10_HashtableIjSt4pairIKjmESaIS2_ENSt8__detail10_Select1stESt8equal_toIjESt4hashIjENS4_18_Mod_range_hashingENS4_20_Default_ranged_hashENS4_20_Prime_rehash_policyENS4_17_Hashtable_traitsILb0ELb0ELb0EEEE9_M_rehashEmRKm
.LEHE52:
	jmp	.L3301
.L3538:
	xorl	%edx, %edx
	jmp	.L3087
.L3080:
	leal	-1(%r13), %edx
	cmpl	$6, %edx
	jbe	.L3546
	vmovapd	.LC74(%rip), %ymm7
	vpbroadcastd	%r13d, %ymm0
	movl	%r13d, %ecx
	vcvtdq2pd	%xmm0, %ymm1
	vextracti128	$0x1, %ymm0, %xmm0
	andl	$-8, %ecx
	vcvtdq2pd	%xmm0, %ymm0
	movl	%ecx, %edx
	vdivpd	%ymm1, %ymm7, %ymm1
	vdivpd	%ymm0, %ymm7, %ymm0
	vmovapd	%ymm1, -9584(%rbp)
	vmovapd	%ymm0, -9552(%rbp)
	cmpl	%r13d, %ecx
	je	.L3085
.L3096:
	movl	%r13d, %esi
	subl	%ecx, %esi
	leal	-1(%rsi), %edi
	cmpl	$2, %edi
	jbe	.L3098
	vmovddup	.LC1(%rip), %xmm1
	vpbroadcastd	%r13d, %xmm0
	leaq	-9584(%rbp,%rcx,8), %rcx
	vcvtdq2pd	%xmm0, %xmm2
	vpshufd	$238, %xmm0, %xmm0
	vcvtdq2pd	%xmm0, %xmm0
	vdivpd	%xmm2, %xmm1, %xmm2
	vdivpd	%xmm0, %xmm1, %xmm1
	vmovapd	%xmm2, (%rcx)
	vmovapd	%xmm1, 16(%rcx)
	movl	%esi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %edx
	cmpl	%esi, %ecx
	je	.L3085
.L3098:
	vxorpd	%xmm7, %xmm7, %xmm7
	movslq	%edx, %rcx
	vcvtsi2sdl	%r13d, %xmm7, %xmm0
	vmovsd	.LC1(%rip), %xmm7
	vdivsd	%xmm0, %xmm7, %xmm0
	vmovsd	%xmm0, -9584(%rbp,%rcx,8)
	leal	1(%rdx), %ecx
	cmpl	%ecx, %r13d
	jle	.L3085
	movslq	%ecx, %rcx
	addl	$2, %edx
	vmovsd	%xmm0, -9584(%rbp,%rcx,8)
	cmpl	%edx, %r13d
	jg	.L4027
	jmp	.L3085
.L3546:
	xorl	%edx, %edx
	xorl	%ecx, %ecx
	jmp	.L3096
.L4044:
	vxorpd	%xmm7, %xmm7, %xmm7
	leal	-1(%r13), %edx
	leaq	-9584(%rbp), %r12
	vmovsd	%xmm7, -10040(%rbp)
	vmovsd	.LC70(%rip), %xmm7
	leaq	-9576(%rbp,%rdx,8), %rbx
	vmovq	%xmm7, %r14
	vmovsd	.LC1(%rip), %xmm7
	vmovsd	%xmm7, -10232(%rbp)
.L3086:
	movq	2792(%r15), %rax
	cmpq	$311, %rax
	ja	.L4076
.L3082:
	leaq	1(%rax), %rdx
	movabsq	$6148914691236517205, %rcx
	vxorpd	%xmm7, %xmm7, %xmm7
	movq	%rdx, 2792(%r15)
	movq	296(%r15,%rax,8), %rdx
	movq	%rdx, %rax
	shrq	$29, %rax
	andq	%rcx, %rax
	movabsq	$8202884508482404352, %rcx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rcx, %rdx
	movabsq	$-2270628950310912, %rcx
	xorq	%rax, %rdx
	movq	%rdx, %rax
	salq	$37, %rax
	andq	%rcx, %rax
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	vcvtusi2sdq	%rax, %xmm7, %xmm0
	vaddsd	-10040(%rbp), %xmm0, %xmm0
	vmovq	%r14, %xmm7
	vmulsd	%xmm7, %xmm0, %xmm0
	vcomisd	-10232(%rbp), %xmm0
	jnb	.L3083
	vmovsd	.LC72(%rip), %xmm7
	addq	$8, %r12
	vfmadd132sd	.LC71(%rip), %xmm7, %xmm0
	call	log@PLT
	vxorpd	.LC6(%rip), %xmm0, %xmm0
	vmovsd	%xmm0, -8(%r12)
	cmpq	%rbx, %r12
	je	.L3085
	movq	2792(%r15), %rax
	cmpq	$311, %rax
	jbe	.L3082
.L4076:
	leaq	296(%r15), %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2792(%r15), %rax
	jmp	.L3082
.L3128:
	leaq	-9456(%rbp), %rdi
	movl	$14, %ecx
	xorl	%eax, %eax
	movl	$0, -9904(%rbp)
	movq	%rdi, -10088(%rbp)
	rep stosq
	jmp	.L3155
	.p2align 4
	.p2align 3
.L4058:
	movq	%r12, %rcx
	movl	%r14d, %r12d
	movq	%rcx, %r14
.L3123:
	cmpl	%eax, %r12d
	je	.L3126
	addq	$16, %rdi
	cmpq	%r14, %rdi
	jne	.L3127
	jmp	.L3126
.L3083:
	movq	.LC73(%rip), %rax
	addq	$8, %r12
	movq	%rax, -8(%r12)
	cmpq	%rbx, %r12
	jne	.L3086
	jmp	.L3085
.L4041:
	movq	$0, -10144(%rbp)
	movq	$0, -10064(%rbp)
	jmp	.L3060
.L3053:
	movq	$0, -9936(%rbp)
	movq	$0, -9920(%rbp)
	xorl	%edx, %edx
	jmp	.L3532
.L4037:
	leaq	.LC11(%rip), %rdi
.LEHB53:
	call	_ZSt20__throw_length_errorPKc@PLT
.LEHE53:
	.p2align 4
	.p2align 3
.L4024:
	vzeroupper
	jmp	.L3278
.L3585:
	xorl	%edx, %edx
	xorl	%eax, %eax
	jmp	.L3283
	.p2align 4
	.p2align 3
.L3294:
	leaq	-9648(%rbp), %rax
	leaq	-9872(%rbp), %rdi
	movq	%rax, %rdx
.LEHB54:
	call	_ZNSt6vectorISt4pairIjmESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
.LEHE54:
	jmp	.L3293
.L3298:
	movq	$0, -9672(%rbp)
	jmp	.L3299
	.p2align 4
	.p2align 3
.L3460:
	movq	-10240(%rbp), %rax
	andl	$1023, %eax
	cmpq	$1023, %rax
	je	.L3455
.L3458:
	incq	-10240(%rbp)
	addq	$16, -10408(%rbp)
	movq	-10240(%rbp), %rax
	cmpq	-10528(%rbp), %rax
	jne	.L3456
.L3459:
	movq	-9800(%rbp), %r12
	movq	-9808(%rbp), %rbx
	movq	-9792(%rbp), %r15
	movq	%r12, %r13
	subq	%rbx, %r13
	cmpq	%r12, %rbx
	je	.L3461
	movq	%r13, %rax
	movl	$63, %edx
	movq	%r12, %rsi
	movq	%rbx, %rdi
	sarq	$4, %rax
	lzcntq	%rax, %rax
	subl	%eax, %edx
	movslq	%edx, %rdx
	addq	%rdx, %rdx
	call	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElNS0_5__ops15_Iter_less_iterEEvT_SA_T0_T1_.isra.0
	cmpq	$256, %r13
	jle	.L3462
	leaq	256(%rbx), %r14
	movq	%rbx, %rdi
	movq	%r14, %rsi
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0
	movq	%r14, %rax
	cmpq	%r14, %r12
	je	.L3461
.L3470:
	vmovsd	(%rax), %xmm0
	movq	8(%rax), %rsi
	movq	%rax, %rdx
	jmp	.L3465
.L3466:
	subq	$16, %rdx
	cmpq	-8(%rcx), %rsi
	jnb	.L3469
.L3468:
	vmovdqu	(%rdx), %xmm7
	vmovdqu	%xmm7, 16(%rdx)
.L3465:
	vmovsd	-16(%rdx), %xmm1
	movq	%rdx, %rcx
	vucomisd	%xmm1, %xmm0
	jp	.L3645
	je	.L3466
.L3645:
	subq	$16, %rdx
	vcomisd	%xmm0, %xmm1
	ja	.L3468
.L3469:
	addq	$16, %rax
	vmovsd	%xmm0, (%rcx)
	movq	%rsi, 8(%rcx)
	cmpq	%r12, %rax
	jne	.L3470
.L3461:
	movq	%r12, %r14
	cmpq	$8192, %r13
	ja	.L4077
.L3312:
	leaq	_ZSt4cerr(%rip), %r12
	leaq	-9648(%rbp), %rax
	movl	$17, %edx
	leaq	.LC79(%rip), %rsi
	movq	%r12, %rdi
	movq	%rax, -10112(%rbp)
.LEHB55:
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	-10360(%rbp), %rsi
	leaq	-9648(%rbp), %rax
	movq	%r12, %rdi
	movq	%rax, -10112(%rbp)
	call	_ZNSo9_M_insertImEERSoT_@PLT
	movq	%rax, %r12
	movl	$7, %edx
	leaq	-9648(%rbp), %rax
	leaq	.LC62(%rip), %rsi
	movq	%r12, %rdi
	movq	%rax, -10112(%rbp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	%r13, %rsi
	leaq	-9648(%rbp), %rax
	movq	%r12, %rdi
	sarq	$4, %rsi
	movq	%rax, -10112(%rbp)
	call	_ZNSo9_M_insertImEERSoT_@PLT
	movq	%rax, %rdi
	movl	$1, %edx
	leaq	-9648(%rbp), %rax
	leaq	.LC63(%rip), %rsi
	movq	%rax, -10112(%rbp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	-10416(%rbp), %rax
	vmovq	%rbx, %xmm7
	movq	-9632(%rbp), %rbx
	vpinsrq	$1, %r14, %xmm7, %xmm0
	vmovdqu	%xmm0, (%rax)
	movq	%r15, 16(%rax)
	testq	%rbx, %rbx
	je	.L3475
.L3472:
	movq	%rbx, %rdi
	movl	$16, %esi
	movq	(%rbx), %rbx
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L3472
.L3475:
	movq	-9640(%rbp), %rax
	movq	-9648(%rbp), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	-9640(%rbp), %rsi
	movq	$0, -9624(%rbp)
	movq	$0, -9632(%rbp)
	movq	-9648(%rbp), %rdi
	cmpq	-10424(%rbp), %rdi
	je	.L3473
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L3473:
	movq	-10152(%rbp), %rax
	testq	%rax, %rax
	je	.L3476
	movq	-10392(%rbp), %rsi
	movq	%rax, %rdi
	call	_ZdlPvm@PLT
.L3476:
	movq	-9696(%rbp), %rbx
	testq	%rbx, %rbx
	je	.L3480
.L3477:
	movq	%rbx, %rdi
	movq	(%rbx), %rbx
	movl	$24, %esi
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L3477
.L3480:
	movq	-9704(%rbp), %rax
	movq	-9712(%rbp), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	-9704(%rbp), %rsi
	movq	$0, -9688(%rbp)
	movq	$0, -9696(%rbp)
	movq	-9712(%rbp), %rdi
	cmpq	-10480(%rbp), %rdi
	je	.L3478
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L3478:
	movq	-10128(%rbp), %rax
	testq	%rax, %rax
	je	.L3481
	movq	-10400(%rbp), %rsi
	movq	%rax, %rdi
	subq	%rax, %rsi
	call	_ZdlPvm@PLT
.L3481:
	movq	-10488(%rbp), %rax
	testq	%rax, %rax
	je	.L3482
	movq	-9824(%rbp), %rsi
	movq	%rax, %rdi
	subq	%rax, %rsi
	call	_ZdlPvm@PLT
.L3482:
	movq	-10256(%rbp), %rax
	testq	%rax, %rax
	je	.L3483
	movq	-9856(%rbp), %rsi
	movq	%rax, %rdi
	subq	%rax, %rsi
	call	_ZdlPvm@PLT
.L3483:
	movq	-9760(%rbp), %rbx
	testq	%rbx, %rbx
	je	.L3487
.L3484:
	movq	%rbx, %rdi
	movq	(%rbx), %rbx
	movl	$16, %esi
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L3484
.L3487:
	movq	-9768(%rbp), %rax
	movq	-9776(%rbp), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	-9768(%rbp), %rsi
	movq	$0, -9752(%rbp)
	movq	$0, -9760(%rbp)
	movq	-9776(%rbp), %rdi
	cmpq	-10536(%rbp), %rdi
	je	.L3485
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L3485:
	movq	-10440(%rbp), %rax
	testq	%rax, %rax
	je	.L3488
	movq	-9888(%rbp), %rsi
	movq	%rax, %rdi
	subq	%rax, %rsi
	call	_ZdlPvm@PLT
.L3488:
	movq	-9928(%rbp), %rbx
	movq	-9936(%rbp), %r12
	cmpq	%r12, %rbx
	je	.L3489
.L3493:
	movq	(%r12), %rdi
	testq	%rdi, %rdi
	je	.L3490
	movq	16(%r12), %rsi
	addq	$32, %r12
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	cmpq	%rbx, %r12
	jne	.L3493
.L3492:
	movq	-9936(%rbp), %r12
.L3489:
	testq	%r12, %r12
	je	.L3046
	movq	-9920(%rbp), %rsi
	movq	%r12, %rdi
	subq	%r12, %rsi
	call	_ZdlPvm@PLT
	jmp	.L3046
	.p2align 4
	.p2align 3
.L4068:
	movq	(%rdx), %rdx
	testq	%rdx, %rdx
	jne	.L3317
	movq	%rdx, -10352(%rbp)
	jmp	.L3318
.L4077:
	leaq	8192(%rbx), %r14
	cmpq	%r14, %r12
	je	.L3312
	movq	%r14, -9800(%rbp)
	movl	$8192, %r13d
	jmp	.L3312
	.p2align 4
	.p2align 3
.L3324:
	vmovsd	16(%rsi), %xmm5
	vmovsd	%xmm5, -10144(%rbp)
.L3421:
	vmovsd	-10432(%rbp), %xmm7
	vmovsd	-10144(%rbp), %xmm5
	movq	-10224(%rbp), %rax
	vcomisd	%xmm5, %xmm7
	cmova	-10368(%rbp), %rax
	vminsd	%xmm7, %xmm5, %xmm5
	vmovsd	%xmm5, -10432(%rbp)
	movq	%rax, -10224(%rbp)
.L3322:
	incl	-10248(%rbp)
	movl	-10248(%rbp), %eax
	cmpl	%ecx, %eax
	jl	.L3449
	movq	-10224(%rbp), %rsi
	movl	8(%r15), %eax
	popcntq	%rsi, %rcx
	movq	%rsi, -10024(%rbp)
	movl	%ecx, %edx
	cmpl	%eax, %ecx
	jge	.L3321
	movq	%rsi, -10448(%rbp)
	jmp	.L3320
.L4073:
	movq	-10464(%rbp), %rdx
	vmovsd	-9520(%rbp), %xmm8
	movq	%r13, %rbx
	movq	-10048(%rbp), %r15
	cmpq	%r13, %rdx
	je	.L3595
	leaq	-9512(%rbp), %rax
	vmovsd	%xmm8, %xmm8, %xmm4
	cmpq	%rax, %rdx
	je	.L3374
	.p2align 4
	.p2align 3
.L3376:
	vmovsd	(%rax), %xmm0
	addq	$8, %rax
	vmaxsd	%xmm4, %xmm0, %xmm4
	cmpq	%rax, %rdx
	jne	.L3376
.L3374:
	testl	%r14d, %r14d
	jle	.L3598
.L4086:
	vaddsd	-10040(%rbp), %xmm8, %xmm8
	cmpl	$1, %r14d
	je	.L3377
	vaddsd	-9512(%rbp), %xmm8, %xmm8
	cmpl	$2, %r14d
	je	.L3377
	vaddsd	-9504(%rbp), %xmm8, %xmm8
	cmpl	$3, %r14d
	je	.L3377
	vaddsd	-9496(%rbp), %xmm8, %xmm8
	cmpl	$4, %r14d
	je	.L3377
	vaddsd	-9488(%rbp), %xmm8, %xmm8
	cmpl	$5, %r14d
	je	.L3377
	vaddsd	-9480(%rbp), %xmm8, %xmm8
	cmpl	$6, %r14d
	je	.L3377
	vaddsd	-9472(%rbp), %xmm8, %xmm8
	cmpl	$7, %r14d
	je	.L3377
	vaddsd	-9464(%rbp), %xmm8, %xmm8
.L3377:
	movq	%rbx, %rdi
	movl	$3, -10120(%rbp)
	movl	%r14d, %ebx
	.p2align 4
	.p2align 3
.L3379:
	movq	-10096(%rbp), %r12
	movq	%r15, %r14
	xorl	%eax, %eax
	movl	%ebx, %r15d
	movq	-10088(%rbp), %r13
	movq	%r12, %rbx
	jmp	.L3395
	.p2align 4
	.p2align 3
.L3522:
	vsubsd	%xmm4, %xmm1, %xmm2
	vandpd	.LC5(%rip), %xmm2, %xmm2
	vcomisd	%xmm2, %xmm5
	jbe	.L3390
	vsubsd	%xmm5, %xmm8, %xmm2
	vcomisd	%xmm0, %xmm2
	ja	.L4078
.L3390:
	addq	$64, %rbx
	addq	$4, %r13
	cmpq	%r14, %rbx
	je	.L4079
.L3395:
	vsubsd	%xmm5, %xmm4, %xmm6
	testl	%r15d, %r15d
	jle	.L3380
	movl	0(%r13), %r12d
	vxorpd	%xmm1, %xmm1, %xmm1
	vmovsd	(%rbx), %xmm0
	vcvtsi2sdl	%r12d, %xmm1, %xmm2
	vfmadd213sd	-9520(%rbp), %xmm2, %xmm0
	vmaxsd	%xmm7, %xmm0, %xmm1
	vmovsd	%xmm0, -9456(%rbp)
	vaddsd	-10040(%rbp), %xmm0, %xmm0
	cmpl	$1, %r15d
	je	.L3382
	vmovsd	8(%rbx), %xmm3
	vfmadd213sd	-9512(%rbp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, -9448(%rbp)
	cmpl	$2, %r15d
	je	.L3382
	vmovsd	16(%rbx), %xmm3
	vfmadd213sd	-9504(%rbp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, -9440(%rbp)
	cmpl	$3, %r15d
	je	.L3382
	vmovsd	24(%rbx), %xmm3
	vfmadd213sd	-9496(%rbp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, -9432(%rbp)
	cmpl	$4, %r15d
	je	.L3382
	vmovsd	32(%rbx), %xmm3
	vfmadd213sd	-9488(%rbp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, -9424(%rbp)
	cmpl	$5, %r15d
	je	.L3382
	vmovsd	40(%rbx), %xmm3
	vfmadd213sd	-9480(%rbp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, -9416(%rbp)
	cmpl	$6, %r15d
	je	.L3382
	vmovsd	48(%rbx), %xmm3
	vfmadd213sd	-9472(%rbp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, -9408(%rbp)
	cmpl	$7, %r15d
	je	.L3382
	vmovsd	-9464(%rbp), %xmm3
	vfmadd132sd	56(%rbx), %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm2, %xmm1
	vaddsd	%xmm2, %xmm0, %xmm0
	vmovsd	%xmm2, -9400(%rbp)
.L3382:
	vcomisd	%xmm1, %xmm6
	jbe	.L3522
.L3394:
	movq	-10080(%rbp), %rdx
	leaq	-9456(%rbp), %rsi
	vmovsd	%xmm7, -10064(%rbp)
	vmovsd	%xmm1, -10056(%rbp)
	vmovsd	%xmm0, -10048(%rbp)
	vzeroupper
	call	memcpy@PLT
	vmovsd	-10056(%rbp), %xmm1
	vmovsd	-10048(%rbp), %xmm0
	vmovsd	-10064(%rbp), %xmm7
	movq	%rax, %rdi
	movq	.LC47(%rip), %rax
	vmovq	%rax, %xmm5
	vmovsd	%xmm1, %xmm1, %xmm4
	vmovsd	%xmm0, %xmm0, %xmm8
.L3393:
	negl	%r12d
	addq	$64, %rbx
	movzbl	-10068(%rbp), %eax
	addq	$4, %r13
	movl	%r12d, -4(%r13)
	cmpq	%r14, %rbx
	jne	.L3395
.L4079:
	movl	%r15d, %ebx
	movq	%r14, %r15
	testb	%al, %al
	je	.L3396
	decl	-10120(%rbp)
	jne	.L3379
.L3396:
	vmovsd	-10144(%rbp), %xmm6
	movl	%ebx, %r14d
	movq	%rdi, %rbx
	vcomisd	%xmm4, %xmm6
	jbe	.L4080
.L3397:
	movq	-10496(%rbp), %rdx
	movq	-10088(%rbp), %rsi
	vmovsd	%xmm7, -10064(%rbp)
	vmovsd	%xmm8, -10056(%rbp)
	vmovsd	%xmm4, -10048(%rbp)
	movq	-10136(%rbp), %rdi
	vzeroupper
	call	memcpy@PLT
	vmovsd	-10056(%rbp), %xmm8
	vmovsd	-10048(%rbp), %xmm4
	vmovsd	-10064(%rbp), %xmm7
	movq	.LC47(%rip), %rax
	vmovq	%rax, %xmm5
	vmovsd	%xmm8, -10456(%rbp)
	vmovsd	%xmm4, -10144(%rbp)
.L3398:
	movq	-10464(%rbp), %rcx
	cmpq	%rbx, %rcx
	je	.L3608
.L4085:
	leaq	-9512(%rbp), %rax
	cmpq	%rax, %rcx
	je	.L3608
	movq	%rbx, %rdx
	.p2align 4
	.p2align 3
.L3403:
	vmovsd	(%rax), %xmm0
	vucomisd	(%rdx), %xmm0
	cmova	%rax, %rdx
	addq	$8, %rax
	cmpq	%rcx, %rax
	jne	.L3403
	subq	%rbx, %rdx
	sarq	$3, %rdx
.L3400:
	testl	%r14d, %r14d
	jle	.L3408
	cmpl	$6, -10104(%rbp)
	jbe	.L3610
	vpbroadcastd	%edx, %ymm0
	movl	-10072(%rbp), %eax
	vpcmpd	$0, .LC48(%rip), %ymm0, %k1
	vbroadcastsd	.LC54(%rip), %ymm0
	vmovapd	.LC49(%rip), %ymm1{%k1}{z}
	kshiftrb	$4, %k1, %k1
	vfmadd231pd	-9584(%rbp), %ymm0, %ymm1
	vmovapd	.LC49(%rip), %ymm2{%k1}{z}
	vfmadd132pd	-9552(%rbp), %ymm2, %ymm0
	movl	%eax, %ecx
	vmovapd	%ymm1, -9584(%rbp)
	vmovapd	%ymm0, -9552(%rbp)
	cmpl	%eax, %r14d
	je	.L3408
.L3406:
	movl	%r14d, %esi
	subl	%ecx, %esi
	leal	-1(%rsi), %edi
	cmpl	$2, %edi
	jbe	.L3409
	vpbroadcastd	%eax, %xmm0
	vpaddd	.LC51(%rip), %xmm0, %xmm0
	vpbroadcastd	%edx, %xmm1
	leaq	-9584(%rbp,%rcx,8), %rcx
	vpcmpd	$0, %xmm1, %xmm0, %k1
	vmovddup	.LC44(%rip), %xmm0
	vmovapd	%xmm0, %xmm1{%k1}{z}
	kshiftrb	$2, %k1, %k1
	vmovapd	%xmm0, %xmm2{%k1}{z}
	vmovddup	.LC54(%rip), %xmm0
	vfmadd231pd	(%rcx), %xmm0, %xmm1
	vfmadd132pd	16(%rcx), %xmm2, %xmm0
	vmovapd	%xmm1, (%rcx)
	vmovapd	%xmm0, 16(%rcx)
	movl	%esi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %eax
	cmpl	%ecx, %esi
	je	.L3408
.L3409:
	vmovsd	.LC54(%rip), %xmm0
	movslq	%eax, %rcx
	vxorpd	%xmm1, %xmm1, %xmm1
	vmulsd	-9584(%rbp,%rcx,8), %xmm0, %xmm2
	cmpl	%edx, %eax
	je	.L4081
.L3411:
	vaddsd	%xmm2, %xmm1, %xmm1
	vmovsd	%xmm1, -9584(%rbp,%rcx,8)
	leal	1(%rax), %ecx
	cmpl	%ecx, %r14d
	jle	.L3408
	movslq	%ecx, %rsi
	vxorpd	%xmm1, %xmm1, %xmm1
	vmulsd	-9584(%rbp,%rsi,8), %xmm0, %xmm2
	cmpl	%edx, %ecx
	je	.L4082
.L3412:
	vaddsd	%xmm2, %xmm1, %xmm1
	addl	$2, %eax
	vmovsd	%xmm1, -9584(%rbp,%rsi,8)
	cmpl	%eax, %r14d
	jle	.L3408
	movslq	%eax, %rcx
	vxorpd	%xmm1, %xmm1, %xmm1
	vmulsd	-9584(%rbp,%rcx,8), %xmm0, %xmm0
	cmpl	%edx, %eax
	je	.L4083
.L3413:
	vaddsd	%xmm1, %xmm0, %xmm0
	vmovsd	%xmm0, -9584(%rbp,%rcx,8)
.L3408:
	cmpl	$1, -10468(%rbp)
	je	.L4084
	movl	$1, -10468(%rbp)
	jmp	.L3351
	.p2align 4
	.p2align 3
.L3380:
	vmovsd	%xmm7, %xmm7, %xmm1
	vxorpd	%xmm0, %xmm0, %xmm0
	vcomisd	%xmm7, %xmm6
	jbe	.L3522
	movl	0(%r13), %r12d
	vmovsd	%xmm7, %xmm7, %xmm4
	vxorpd	%xmm8, %xmm8, %xmm8
	jmp	.L3393
	.p2align 4
	.p2align 3
.L4078:
	movl	0(%r13), %r12d
	testl	%r15d, %r15d
	jg	.L3394
	vmovsd	%xmm1, %xmm1, %xmm4
	vmovsd	%xmm0, %xmm0, %xmm8
	jmp	.L3393
.L4074:
	movl	%r12d, (%rax)
	jmp	.L3369
.L3593:
	xorl	%edi, %edi
	vxorpd	%xmm0, %xmm0, %xmm0
	xorl	%edx, %edx
	jmp	.L3362
.L4080:
	vucomisd	%xmm4, %xmm6
	jp	.L3398
	jne	.L3398
	vmovsd	-10456(%rbp), %xmm6
	vcomisd	%xmm8, %xmm6
	ja	.L3397
	movq	-10464(%rbp), %rcx
	cmpq	%rbx, %rcx
	jne	.L4085
.L3608:
	xorl	%edx, %edx
	jmp	.L3400
.L3595:
	vmovsd	%xmm8, %xmm8, %xmm4
	testl	%r14d, %r14d
	jg	.L4086
.L3598:
	vxorpd	%xmm8, %xmm8, %xmm8
	jmp	.L3377
.L4083:
	vmovsd	.LC44(%rip), %xmm1
	jmp	.L3413
.L4082:
	vmovsd	.LC44(%rip), %xmm1
	jmp	.L3412
.L4081:
	vmovsd	.LC44(%rip), %xmm1
	jmp	.L3411
.L4084:
	movq	%r15, %r14
	movq	-10096(%rbp), %rax
	movq	-10552(%rbp), %r15
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqa	%xmm0, -8816(%rbp)
	vmovdqa	%xmm0, -8800(%rbp)
	vxorpd	%xmm1, %xmm1, %xmm1
	vmovdqa	%xmm0, -8784(%rbp)
	vmovdqa	%xmm0, -8768(%rbp)
.L3416:
	vmovapd	(%rax), %zmm5
	addq	$64, %rax
	vandpd	.LC55(%rip), %zmm5, %zmm0
	vaddpd	%zmm0, %zmm1, %zmm1
	cmpq	%r14, %rax
	jne	.L3416
	movq	-10504(%rbp), %rdx
	addq	-10136(%rbp), %rdx
	vmovapd	%ymm1, %ymm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vmovapd	%zmm1, -8816(%rbp)
	cmpq	-10136(%rbp), %rdx
	je	.L3417
	leaq	-8808(%rbp), %rax
	cmpq	%rax, %rdx
	jne	.L3420
	jmp	.L3417
.L4087:
	vmovsd	(%rax), %xmm2
.L3420:
	addq	$8, %rax
	vminsd	%xmm0, %xmm2, %xmm0
	cmpq	%rax, %rdx
	jne	.L4087
.L3417:
	vmovsd	-10232(%rbp), %xmm7
	leaq	-9984(%rbp), %rdx
	leaq	-10016(%rbp), %rsi
	leaq	120(%r15), %rdi
	vsubsd	%xmm0, %xmm7, %xmm0
	vmulsd	.LC43(%rip), %xmm0, %xmm5
	vmovsd	-10144(%rbp), %xmm7
	vmovq	%xmm5, %r13
	vunpcklpd	%xmm5, %xmm7, %xmm0
	vmovapd	%xmm0, -9984(%rbp)
	vzeroupper
	call	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0
	movq	-10016(%rbp), %rbx
	popcntq	%rbx, %rax
	cmpl	8(%r15), %eax
	je	.L3986
.L4031:
	movl	4(%r15), %ecx
	jmp	.L3421
.L3610:
	xorl	%ecx, %ecx
	xorl	%eax, %eax
	jmp	.L3406
.L4069:
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	cmpq	%rax, 2832(%r15)
	jg	.L3327
	movb	$1, 2840(%r15)
	jmp	.L3327
.L3592:
	xorl	%edx, %edx
	xorl	%eax, %eax
	jmp	.L3357
.L3321:
	cmpl	%edx, %eax
	jne	.L3452
	movq	-10224(%rbp), %rsi
	movq	%r15, %rdi
	call	_ZN9Optimizer8evaluateEmb.constprop.0
	movq	-10224(%rbp), %rax
	leaq	-9952(%rbp), %rsi
	leaq	-9808(%rbp), %rdi
	vmovsd	%xmm0, -9952(%rbp)
	movq	%rax, -9944(%rbp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	jmp	.L3452
.L3591:
	xorl	%edx, %edx
	xorl	%eax, %eax
	jmp	.L3352
.L4072:
	leal	-1(%r12), %eax
	movl	%eax, -10104(%rbp)
	jmp	.L3354
.L3986:
	vmovsd	2848(%r15), %xmm0
	vmovsd	-10144(%rbp), %xmm7
	movq	%rbx, -10008(%rbp)
	vcomisd	%xmm7, %xmm0
	jbe	.L3422
	vmovsd	%xmm7, 2848(%r15)
	movq	%rbx, 2856(%r15)
.L3422:
	movq	208(%r15), %rdx
	movq	216(%r15), %rax
	subq	%rdx, %rax
	cmpq	$1520, %rax
	jbe	.L3424
	vmovsd	(%rdx), %xmm0
	vmovq	%r13, %xmm7
	vcomisd	%xmm7, %xmm0
	jbe	.L3425
.L3424:
	leaq	-9968(%rbp), %rsi
	leaq	208(%r15), %rdi
	movq	%r13, -9968(%rbp)
	movq	%rbx, -9960(%rbp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	216(%r15), %r8
	movq	208(%r15), %rdi
	movq	%r8, %rsi
	vmovsd	-16(%r8), %xmm0
	movq	-8(%r8), %r10
	subq	%rdi, %rsi
	movq	%rsi, %rdx
	sarq	$4, %rdx
	leaq	-1(%rdx), %rax
	subq	$2, %rdx
	movq	%rdx, %rcx
	shrq	$63, %rcx
	addq	%rdx, %rcx
	sarq	%rcx
	testq	%rax, %rax
	jg	.L3430
	jmp	.L4088
	.p2align 4
	.p2align 3
.L3427:
	cmpq	%r10, 8(%r9)
	setb	%dl
.L3429:
	salq	$4, %rax
	addq	%rdi, %rax
	testb	%dl, %dl
	je	.L3431
	vmovdqu	(%r9), %xmm5
	vmovdqu	%xmm5, (%rax)
	leaq	-1(%rcx), %rax
	movq	%rax, %rdx
	shrq	$63, %rdx
	addq	%rax, %rdx
	movq	%rcx, %rax
	sarq	%rdx
	testq	%rcx, %rcx
	jle	.L4089
	movq	%rdx, %rcx
.L3430:
	movq	%rcx, %r9
	salq	$4, %r9
	addq	%rdi, %r9
	vmovsd	(%r9), %xmm1
	vucomisd	%xmm0, %xmm1
	jp	.L3642
	je	.L3427
.L3642:
	vcomisd	%xmm1, %xmm0
	seta	%dl
	jmp	.L3429
.L4088:
	leaq	-16(%rdi,%rsi), %rax
.L3431:
	vmovsd	%xmm0, (%rax)
	movq	%r10, 8(%rax)
	cmpq	$1536, %rsi
	ja	.L4090
.L3425:
	movq	176(%r15), %rdx
	movq	184(%r15), %rax
	subq	%rdx, %rax
	cmpq	$1520, %rax
	jbe	.L3434
	vmovsd	-10144(%rbp), %xmm5
	vcomisd	(%rdx), %xmm5
	jnb	.L4031
.L3434:
	movq	248(%r15), %rdi
	movq	%rbx, %rax
	xorl	%edx, %edx
	divq	%rdi
	movq	240(%r15), %rax
	movq	(%rax,%rdx,8), %rax
	movq	%rdx, %r8
	testq	%rax, %rax
	je	.L3437
	movq	(%rax), %rcx
	movq	8(%rcx), %rsi
.L3439:
	cmpq	%rsi, %rbx
	je	.L4031
	movq	(%rcx), %rcx
	testq	%rcx, %rcx
	je	.L3437
	movq	8(%rcx), %rsi
	xorl	%edx, %edx
	movq	%rsi, %rax
	divq	%rdi
	cmpq	%rdx, %r8
	je	.L3439
.L3437:
	vmovsd	-10144(%rbp), %xmm7
	leaq	-9952(%rbp), %rsi
	leaq	176(%r15), %rdi
	movq	%rbx, -9944(%rbp)
	vmovsd	%xmm7, -9952(%rbp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	184(%r15), %rax
	movq	176(%r15), %rdx
	vmovsd	-16(%rax), %xmm0
	movq	-8(%rax), %r8
	subq	%rdx, %rax
	movq	%rax, %rdi
	movq	%rax, %rcx
	sarq	$4, %rdi
	leaq	-1(%rdi), %rax
	subq	$2, %rdi
	movq	%rdi, %rsi
	shrq	$63, %rsi
	addq	%rdi, %rsi
	sarq	%rsi
	testq	%rax, %rax
	jg	.L3444
	jmp	.L4091
	.p2align 4
	.p2align 3
.L3441:
	cmpq	8(%rdi), %r8
	seta	%cl
.L3443:
	salq	$4, %rax
	addq	%rdx, %rax
	testb	%cl, %cl
	je	.L3445
	vmovdqu	(%rdi), %xmm5
	vmovdqu	%xmm5, (%rax)
	leaq	-1(%rsi), %rax
	movq	%rax, %rcx
	shrq	$63, %rcx
	addq	%rax, %rcx
	movq	%rsi, %rax
	sarq	%rcx
	testq	%rsi, %rsi
	jle	.L4092
	movq	%rcx, %rsi
.L3444:
	movq	%rsi, %rdi
	salq	$4, %rdi
	addq	%rdx, %rdi
	vmovsd	(%rdi), %xmm1
	vucomisd	%xmm1, %xmm0
	jp	.L3643
	je	.L3441
.L3643:
	vcomisd	%xmm1, %xmm0
	seta	%cl
	jmp	.L3443
.L4090:
	leaq	-16(%r8), %r13
	cmpq	$16, %rsi
	jg	.L4093
.L3433:
	movq	%r13, 216(%r15)
	jmp	.L3425
.L4089:
	movq	%r9, %rax
	jmp	.L3431
.L4093:
	vmovdqu	(%rdi), %xmm7
	movq	-16(%r8), %rax
	movq	%r13, %rdx
	xorl	%esi, %esi
	movq	-8(%r8), %rcx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovq	%rax, %xmm0
	vmovdqu	%xmm7, -16(%r8)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	jmp	.L3433
.L4092:
	movq	%rdi, %rax
.L3445:
	leaq	240(%r15), %r13
	vmovsd	%xmm0, (%rax)
	movq	%r8, 8(%rax)
	leaq	-10008(%rbp), %rsi
	movq	%r13, %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
.LEHE55:
	movq	176(%r15), %rdx
	movq	184(%r15), %rax
	subq	%rdx, %rax
	cmpq	$1536, %rax
	jbe	.L4031
	movq	8(%rdx), %rsi
	movq	%r13, %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE8_M_eraseESt17integral_constantIbLb1EERKm.isra.0
	movq	184(%r15), %rax
	movq	176(%r15), %rdi
	movq	%rax, %rdx
	leaq	-16(%rax), %rbx
	subq	%rdi, %rdx
	cmpq	$16, %rdx
	jg	.L3446
.L3447:
	movq	%rbx, 184(%r15)
	jmp	.L4031
.L4091:
	leaq	-16(%rdx,%rcx), %rax
	jmp	.L3445
.L3446:
	vmovdqu	(%rdi), %xmm7
	movq	-16(%rax), %rdx
	xorl	%esi, %esi
	movq	-8(%rax), %rcx
	vmovq	%rdx, %xmm0
	movq	%rbx, %rdx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm7, -16(%rax)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	jmp	.L3447
.L3490:
	addq	$32, %r12
	cmpq	%r12, %rbx
	jne	.L3493
	jmp	.L3492
.L3462:
	movq	%r12, %rsi
	movq	%rbx, %rdi
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0
	jmp	.L3461
.L4066:
	xorl	%r15d, %r15d
	xorl	%ebx, %ebx
	xorl	%r13d, %r13d
	xorl	%r14d, %r14d
	jmp	.L3312
	.p2align 4
	.p2align 3
.L3455:
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	cmpq	%rax, -10384(%rbp)
	jg	.L3458
	jmp	.L3459
.L3629:
	endbr64
	movq	%rax, %rbx
	jmp	.L3503
.L3631:
	endbr64
	movq	%rax, %rbx
	jmp	.L3307
.L3620:
	endbr64
	movq	%rax, %rbx
	jmp	.L3500
.L3628:
	endbr64
	movq	%rax, %rbx
	jmp	.L3308
.L3623:
	endbr64
	movq	%rax, %rbx
	jmp	.L3495
.L3503:
	movq	-9808(%rbp), %rdi
	movq	-9792(%rbp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L4025
	vzeroupper
	call	_ZdlPvm@PLT
.L3504:
	movq	-10112(%rbp), %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED1Ev
	cmpq	$0, -10152(%rbp)
	je	.L3308
	movq	-10392(%rbp), %rsi
	movq	-10152(%rbp), %rdi
	call	_ZdlPvm@PLT
	jmp	.L3308
.L3307:
	movl	$24, %esi
	movq	%r12, %rdi
	vzeroupper
	call	_ZdlPvm@PLT
.L3308:
	movq	-9696(%rbp), %rdi
	vzeroupper
.L3506:
	testq	%rdi, %rdi
	je	.L4094
	movq	(%rdi), %r12
	movl	$24, %esi
	call	_ZdlPvm@PLT
	movq	%r12, %rdi
	jmp	.L3506
.L3495:
	movq	-9712(%rbp), %rdi
	movq	-9696(%rbp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L3497
	vzeroupper
	call	_ZdlPvm@PLT
.L3497:
	movq	-10112(%rbp), %rdi
	vzeroupper
	call	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED1Ev
.L3498:
	movq	-9776(%rbp), %rdi
	movq	-9760(%rbp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L3500
	vzeroupper
	call	_ZdlPvm@PLT
.L3500:
	movq	-10544(%rbp), %rdi
	vzeroupper
	call	_ZNSt6vectorISt14priority_queueI5StateS_IS1_SaIS1_EESt4lessIS1_EESaIS6_EED1Ev
	movq	%rbx, %rdi
.LEHB56:
	call	_Unwind_Resume@PLT
.LEHE56:
.L4025:
	vzeroupper
	jmp	.L3504
.L4094:
	movq	-9704(%rbp), %rax
	movq	-9712(%rbp), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	-9704(%rbp), %rsi
	movq	$0, -9688(%rbp)
	movq	$0, -9696(%rbp)
	movq	-9712(%rbp), %rdi
	cmpq	-10480(%rbp), %rdi
	je	.L3509
	salq	$3, %rsi
	call	_ZdlPvm@PLT
.L3509:
	movq	-10400(%rbp), %rsi
	subq	-10128(%rbp), %rsi
	cmpq	$0, -10128(%rbp)
	je	.L3510
	movq	-10128(%rbp), %rdi
	vzeroupper
	call	_ZdlPvm@PLT
.L3510:
	movq	-9840(%rbp), %rdi
	movq	-9824(%rbp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L3512
.L3534:
	vzeroupper
	call	_ZdlPvm@PLT
.L3512:
	movq	-9872(%rbp), %rdi
	movq	-9856(%rbp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L3513
	vzeroupper
	call	_ZdlPvm@PLT
.L3513:
	leaq	-9776(%rbp), %r13
.L3502:
	movq	%r13, %rdi
	vzeroupper
	call	_ZNSt10_HashtableIjjSaIjENSt8__detail9_IdentityESt8equal_toIjESt4hashIjENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEED1Ev
	movq	-9904(%rbp), %rdi
	movq	-9888(%rbp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L3500
	call	_ZdlPvm@PLT
	jmp	.L3500
.L3632:
	endbr64
	movq	%rax, %rbx
	jmp	.L3533
.L3630:
	endbr64
	movq	%rax, %rbx
	jmp	.L3270
.L3622:
	endbr64
	movq	%rax, %rbx
	jmp	.L3497
.L3626:
	endbr64
	movq	%rax, %rbx
	jmp	.L3512
.L3625:
	endbr64
	movq	%rax, %rbx
	leaq	-9776(%rbp), %r13
	jmp	.L3502
.L3624:
	endbr64
	movq	%rax, %rbx
	jmp	.L3271
.L3533:
	movq	-9840(%rbp), %rdi
	movq	-9824(%rbp), %rsi
	subq	%rdi, %rsi
	jmp	.L3534
.L3270:
	movq	-10064(%rbp), %rdi
	movl	$16, %esi
	vzeroupper
	call	_ZdlPvm@PLT
.L3271:
	movq	-9648(%rbp), %rdi
	movq	-9632(%rbp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L3502
	vzeroupper
	call	_ZdlPvm@PLT
	jmp	.L3502
.L3621:
	endbr64
	movq	%rax, %rbx
	jmp	.L3498
.L3627:
	endbr64
	movq	%rax, %rbx
	jmp	.L3509
	.cfi_endproc
.LFE6027:
	.section	.gcc_except_table
.LLSDA6027:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE6027-.LLSDACSB6027
.LLSDACSB6027:
	.uleb128 .LEHB33-.LFB6027
	.uleb128 .LEHE33-.LEHB33
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB34-.LFB6027
	.uleb128 .LEHE34-.LEHB34
	.uleb128 .L3620-.LFB6027
	.uleb128 0
	.uleb128 .LEHB35-.LFB6027
	.uleb128 .LEHE35-.LEHB35
	.uleb128 .L3624-.LFB6027
	.uleb128 0
	.uleb128 .LEHB36-.LFB6027
	.uleb128 .LEHE36-.LEHB36
	.uleb128 .L3630-.LFB6027
	.uleb128 0
	.uleb128 .LEHB37-.LFB6027
	.uleb128 .LEHE37-.LEHB37
	.uleb128 .L3625-.LFB6027
	.uleb128 0
	.uleb128 .LEHB38-.LFB6027
	.uleb128 .LEHE38-.LEHB38
	.uleb128 .L3626-.LFB6027
	.uleb128 0
	.uleb128 .LEHB39-.LFB6027
	.uleb128 .LEHE39-.LEHB39
	.uleb128 .L3632-.LFB6027
	.uleb128 0
	.uleb128 .LEHB40-.LFB6027
	.uleb128 .LEHE40-.LEHB40
	.uleb128 .L3622-.LFB6027
	.uleb128 0
	.uleb128 .LEHB41-.LFB6027
	.uleb128 .LEHE41-.LEHB41
	.uleb128 .L3621-.LFB6027
	.uleb128 0
	.uleb128 .LEHB42-.LFB6027
	.uleb128 .LEHE42-.LEHB42
	.uleb128 .L3624-.LFB6027
	.uleb128 0
	.uleb128 .LEHB43-.LFB6027
	.uleb128 .LEHE43-.LEHB43
	.uleb128 .L3628-.LFB6027
	.uleb128 0
	.uleb128 .LEHB44-.LFB6027
	.uleb128 .LEHE44-.LEHB44
	.uleb128 .L3631-.LFB6027
	.uleb128 0
	.uleb128 .LEHB45-.LFB6027
	.uleb128 .LEHE45-.LEHB45
	.uleb128 .L3632-.LFB6027
	.uleb128 0
	.uleb128 .LEHB46-.LFB6027
	.uleb128 .LEHE46-.LEHB46
	.uleb128 .L3623-.LFB6027
	.uleb128 0
	.uleb128 .LEHB47-.LFB6027
	.uleb128 .LEHE47-.LEHB47
	.uleb128 .L3627-.LFB6027
	.uleb128 0
	.uleb128 .LEHB48-.LFB6027
	.uleb128 .LEHE48-.LEHB48
	.uleb128 .L3622-.LFB6027
	.uleb128 0
	.uleb128 .LEHB49-.LFB6027
	.uleb128 .LEHE49-.LEHB49
	.uleb128 .L3628-.LFB6027
	.uleb128 0
	.uleb128 .LEHB50-.LFB6027
	.uleb128 .LEHE50-.LEHB50
	.uleb128 .L3629-.LFB6027
	.uleb128 0
	.uleb128 .LEHB51-.LFB6027
	.uleb128 .LEHE51-.LEHB51
	.uleb128 .L3628-.LFB6027
	.uleb128 0
	.uleb128 .LEHB52-.LFB6027
	.uleb128 .LEHE52-.LEHB52
	.uleb128 .L3631-.LFB6027
	.uleb128 0
	.uleb128 .LEHB53-.LFB6027
	.uleb128 .LEHE53-.LEHB53
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB54-.LFB6027
	.uleb128 .LEHE54-.LEHB54
	.uleb128 .L3627-.LFB6027
	.uleb128 0
	.uleb128 .LEHB55-.LFB6027
	.uleb128 .LEHE55-.LEHB55
	.uleb128 .L3629-.LFB6027
	.uleb128 0
	.uleb128 .LEHB56-.LFB6027
	.uleb128 .LEHE56-.LEHB56
	.uleb128 0
	.uleb128 0
.LLSDACSE6027:
	.section	.text._ZN9Optimizer14informed_seedsEv,"axG",@progbits,_ZN9Optimizer14informed_seedsEv,comdat
	.size	_ZN9Optimizer14informed_seedsEv, .-_ZN9Optimizer14informed_seedsEv
	.section	.text._ZN9Optimizer8evaluateEmb,"axG",@progbits,_ZN9Optimizer8evaluateEmb,comdat
	.align 2
	.p2align 4
	.weak	_ZN9Optimizer8evaluateEmb
	.type	_ZN9Optimizer8evaluateEmb, @function
_ZN9Optimizer8evaluateEmb:
.LFB6002:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	andq	$-64, %rsp
	subq	$4096, %rsp
	orq	$0, (%rsp)
	subq	$4096, %rsp
	orq	$0, (%rsp)
	subq	$1472, %rsp
	.cfi_offset 15, -24
	.cfi_offset 14, -32
	.cfi_offset 13, -40
	.cfi_offset 12, -48
	.cfi_offset 3, -56
	movq	%rdi, 112(%rsp)
	movq	%rdi, %rcx
	movq	128(%rdi), %rdi
	movl	%edx, 36(%rsp)
	movq	%rsi, 152(%rsp)
	xorl	%edx, %edx
	movq	%rsi, %rbx
	movq	%fs:40, %rax
	movq	%rax, 9656(%rsp)
	xorl	%eax, %eax
	movq	%rsi, %rax
	divq	%rdi
	movq	120(%rcx), %rax
	movq	(%rax,%rdx,8), %rax
	testq	%rax, %rax
	je	.L4096
	movq	(%rax), %rcx
	movq	%rdx, %r8
	movq	8(%rcx), %rsi
.L4098:
	cmpq	%rsi, %rbx
	je	.L4097
	movq	(%rcx), %rcx
	testq	%rcx, %rcx
	je	.L4096
	movq	8(%rcx), %rsi
	xorl	%edx, %edx
	movq	%rsi, %rax
	divq	%rdi
	cmpq	%rdx, %r8
	je	.L4098
.L4096:
	movq	112(%rsp), %rcx
	movq	2808(%rcx), %rax
	movq	%rax, 144(%rsp)
	incq	%rax
	movq	%rax, 2808(%rcx)
	testb	%al, %al
	je	.L4384
.L4101:
	leaq	896(%rsp), %rax
	xorl	%esi, %esi
	movl	$512, %edx
	movq	%rax, %rdi
	movq	%rax, 80(%rsp)
	call	memset@PLT
	testq	%rbx, %rbx
	vxorps	%xmm7, %xmm7, %xmm7
	je	.L4232
	movq	112(%rsp), %rax
	movl	$1, %edi
	leaq	900(%rsp), %r9
	movq	24(%rax), %r10
	jmp	.L4110
.L4386:
	vpbroadcastd	%edx, %zmm0
	vpxord	896(%rsp), %zmm0, %zmm1
	movq	80(%rsp), %rax
	movl	%edi, %esi
	movslq	%edi, %rcx
	shrl	$4, %esi
	leaq	(%rax,%rcx,4), %rax
	vmovdqu32	%zmm1, (%rax)
	cmpl	$1, %esi
	je	.L4104
	vpxord	960(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 64(%rax)
	cmpl	$2, %esi
	je	.L4104
	vpxord	1024(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 128(%rax)
	cmpl	$3, %esi
	je	.L4104
	vpxord	1088(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 192(%rax)
	cmpl	$4, %esi
	je	.L4104
	vpxord	1152(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 256(%rax)
	cmpl	$5, %esi
	je	.L4104
	vpxord	1216(%rsp), %zmm0, %zmm1
	vmovdqu32	%zmm1, 320(%rax)
	cmpl	$6, %esi
	je	.L4104
	vpxord	1280(%rsp), %zmm0, %zmm0
	vmovdqu32	%zmm0, 384(%rax)
.L4104:
	movl	%edi, %eax
	andl	$-16, %eax
	testb	$15, %dil
	je	.L4109
	movl	%edi, %esi
	subl	%eax, %esi
	leal	-1(%rsi), %r8d
	cmpl	$6, %r8d
	jbe	.L4106
	movl	%eax, %r8d
	vpbroadcastd	%edx, %ymm0
	vpxor	896(%rsp,%r8,4), %ymm0, %ymm0
	addq	%r8, %rcx
	vmovdqu	%ymm0, 896(%rsp,%rcx,4)
	movl	%esi, %ecx
	andl	$-8, %ecx
	addl	%ecx, %eax
	cmpl	%esi, %ecx
	je	.L4109
.L4106:
	movslq	%eax, %rsi
	leal	(%rdi,%rax), %ecx
	movl	896(%rsp,%rsi,4), %r11d
	movslq	%ecx, %rcx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rcx,4)
	leal	1(%rax), %ecx
	cmpl	%ecx, %edi
	jle	.L4109
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	leal	2(%rax), %ecx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%ecx, %edi
	jle	.L4109
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	leal	3(%rax), %ecx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%ecx, %edi
	jle	.L4109
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	leal	4(%rax), %ecx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%ecx, %edi
	jle	.L4109
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	leal	5(%rax), %ecx
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%ecx, %edi
	jle	.L4109
	leal	(%rdi,%rcx), %esi
	movslq	%ecx, %rcx
	addl	$6, %eax
	movl	896(%rsp,%rcx,4), %r11d
	movslq	%esi, %rsi
	xorl	%edx, %r11d
	movl	%r11d, 896(%rsp,%rsi,4)
	cmpl	%eax, %edi
	jle	.L4109
	leal	(%rdi,%rax), %ecx
	cltq
	xorl	896(%rsp,%rax,4), %edx
	movslq	%ecx, %rcx
	movl	%edx, 896(%rsp,%rcx,4)
.L4109:
	addl	%edi, %edi
	blsr	%rbx, %rbx
	je	.L4385
.L4110:
	tzcntq	%rbx, %rax
	leal	-1(%rdi), %ecx
	movl	(%r10,%rax,4), %edx
	cmpl	$14, %ecx
	ja	.L4386
	movq	80(%rsp), %rax
	leaq	(%r9,%rcx,4), %r8
	movslq	%edi, %rcx
.L4108:
	movl	(%rax), %esi
	xorl	%edx, %esi
	movl	%esi, (%rax,%rcx,4)
	addq	$4, %rax
	cmpq	%rax, %r8
	jne	.L4108
	addl	%edi, %edi
	blsr	%rbx, %rbx
	jne	.L4110
.L4385:
	vmovsd	.LC1(%rip), %xmm4
	vcvtsi2sdl	%edi, %xmm7, %xmm3
	movslq	%edi, %rax
	salq	$2, %rax
	movq	%rax, 40(%rsp)
	vdivsd	%xmm3, %xmm4, %xmm3
	vmovsd	%xmm4, 72(%rsp)
.L4102:
	movq	112(%rsp), %r8
	leal	-1(%rdi), %r13d
	leaq	1408(%rsp), %rbx
	movl	$32, %r15d
	movq	80(%rsp), %r11
	movq	%r13, %rax
	movq	%rbx, 120(%rsp)
	salq	$6, %rax
	leaq	1472(%rsp,%rax), %r14
	vmovq	72(%r8), %xmm2
	vmovq	96(%r8), %xmm1
.L4118:
	movl	(%r11), %r10d
	movl	2800(%r8), %eax
	movl	%r10d, %r12d
	cmpl	%eax, (%r8)
	jle	.L4111
	imull	$-1640531535, %r10d, %r12d
	movl	%r15d, %edx
	subl	%eax, %edx
	shrx	%edx, %r12d, %r12d
.L4111:
	vmovq	%xmm2, %rax
	vmovq	%xmm1, %rcx
	leaq	(%rax,%r12,4), %rax
	salq	$6, %r12
	addq	%rcx, %r12
	cmpl	(%rax), %r10d
	je	.L4112
	movq	48(%r8), %rdx
	movq	56(%r8), %rsi
	incq	2816(%r8)
	vbroadcastsd	.LC1(%rip), %zmm0
	movl	%r10d, (%rax)
	cmpq	%rsi, %rdx
	je	.L4113
.L4114:
	movl	(%rdx), %r9d
	xorl	%eax, %eax
	testl	%r9d, %r9d
	jle	.L4117
	movl	4(%rdx), %eax
	andl	%r10d, %eax
	popcntl	%eax, %eax
	andl	$1, %eax
	cmpl	$1, %r9d
	je	.L4117
	movl	8(%rdx), %ecx
	andl	%r10d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	addl	%ecx, %ecx
	orl	%ecx, %eax
	cmpl	$2, %r9d
	je	.L4117
	movl	12(%rdx), %ecx
	andl	%r10d, %ecx
	popcntl	%ecx, %ecx
	andl	$1, %ecx
	sall	$2, %ecx
	orl	%ecx, %eax
.L4117:
	cltq
	addq	$736, %rdx
	salq	$6, %rax
	vmulpd	-512(%rdx,%rax), %zmm0, %zmm0
	cmpq	%rdx, %rsi
	jne	.L4114
.L4113:
	vmovupd	%zmm0, (%r12)
.L4112:
	vmovdqa	(%r12), %xmm4
	addq	$64, %rbx
	addq	$4, %r11
	vmovdqa	32(%r12), %xmm5
	vmovdqa	%xmm4, -64(%rbx)
	vmovdqa	16(%r12), %xmm4
	vmovdqa	%xmm5, -32(%rbx)
	vmovdqa	%xmm4, -48(%rbx)
	vmovdqa	48(%r12), %xmm4
	vmovdqa	%xmm4, -16(%rbx)
	cmpq	%rbx, %r14
	jne	.L4118
	movl	$1, %r9d
	cmpl	$1, %edi
	je	.L4120
.L4119:
	movq	120(%rsp), %rdx
	movslq	%r9d, %rsi
	xorl	%r8d, %r8d
	addl	%r9d, %r9d
	salq	$6, %rsi
	.p2align 4
	.p2align 3
.L4123:
	leaq	(%rdx,%rsi), %rcx
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L4121:
	vmovapd	(%rdx,%rax), %zmm0
	vmovapd	(%rcx,%rax), %zmm1
	vaddpd	%zmm1, %zmm0, %zmm2
	vsubpd	%zmm1, %zmm0, %zmm0
	vmovapd	%zmm2, (%rdx,%rax)
	vmovapd	%zmm0, (%rcx,%rax)
	addq	$64, %rax
	cmpq	%rsi, %rax
	jne	.L4121
	addl	%r9d, %r8d
	leaq	(%rax,%rcx), %rdx
	cmpl	%edi, %r8d
	jl	.L4123
	cmpl	%edi, %r9d
	jl	.L4119
.L4120:
	movq	120(%rsp), %rax
	vbroadcastsd	%xmm3, %zmm3
.L4124:
	vmulpd	(%rax), %zmm3, %zmm0
	addq	$64, %rax
	vmovapd	%zmm0, -64(%rax)
	cmpq	%r14, %rax
	jne	.L4124
	movq	112(%rsp), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqa	%xmm0, 192(%rsp)
	vmovdqa	%xmm0, 208(%rsp)
	vmovdqa	%xmm0, 224(%rsp)
	vmovdqa	%xmm0, 240(%rsp)
	movl	12(%rax), %r15d
	testl	%r15d, %r15d
	jle	.L4387
	vmovsd	72(%rsp), %xmm5
	leal	-1(%r15), %eax
	vcvtsi2sdl	%r15d, %xmm7, %xmm0
	movl	%eax, 108(%rsp)
	vdivsd	%xmm0, %xmm5, %xmm0
	cmpl	$6, %eax
	jbe	.L4236
	movl	%r15d, %edx
	vbroadcastsd	%xmm0, %zmm1
	andl	$-8, %edx
	vmovapd	%zmm1, 192(%rsp)
	movl	%edx, %eax
	cmpl	%r15d, %edx
	je	.L4129
.L4127:
	movl	%r15d, %ecx
	subl	%edx, %ecx
	leal	-1(%rcx), %esi
	cmpl	$2, %esi
	jbe	.L4130
	vbroadcastsd	%xmm0, %ymm1
	vmovapd	%ymm1, 192(%rsp,%rdx,8)
	movl	%ecx, %edx
	andl	$-4, %edx
	addl	%edx, %eax
	cmpl	%ecx, %edx
	je	.L4129
.L4130:
	movslq	%eax, %rdx
	vmovsd	%xmm0, 192(%rsp,%rdx,8)
	leal	1(%rax), %edx
	cmpl	%edx, %r15d
	jle	.L4129
	movslq	%edx, %rdx
	addl	$2, %eax
	vmovsd	%xmm0, 192(%rsp,%rdx,8)
	cmpl	%eax, %r15d
	jle	.L4129
	cltq
	vmovsd	%xmm0, 192(%rsp,%rax,8)
.L4129:
	xorl	%eax, %eax
	testl	%r15d, %r15d
	vmovsd	72(%rsp), %xmm5
	leaq	256(%rsp), %rbx
	setle	%al
	vmovsd	.LC3(%rip), %xmm9
	movl	$2, 64(%rsp)
	vxorpd	%xmm8, %xmm8, %xmm8
	leal	-1(%rax,%rax), %eax
	movl	%eax, 32(%rsp)
	movslq	%r15d, %rax
	salq	$3, %rax
	movq	%rax, 24(%rsp)
	leaq	256(%rsp,%rax), %rax
	movq	%rax, 56(%rsp)
	movl	%r15d, %eax
	andl	$-8, %eax
	testl	%r15d, %r15d
	movl	%eax, 68(%rsp)
	leaq	384(%rsp), %rax
	vmovsd	%xmm5, 48(%rsp)
	vmovsd	%xmm5, 88(%rsp)
	movq	%rax, 96(%rsp)
	leaq	388(%rsp,%r13,4), %rax
	movq	%rax, 8(%rsp)
	movl	$1, %eax
	vmovsd	.LC47(%rip), %xmm5
	cmovg	%r15d, %eax
	movl	%eax, 16(%rsp)
	andl	$-8, %eax
	testl	%r15d, %r15d
	movl	%eax, 20(%rsp)
	movl	108(%rsp), %eax
	leaq	8(,%rax,8), %r13
	movl	$8, %eax
	cmovg	%r13, %rax
	movq	%rax, 128(%rsp)
.L4126:
	testl	%r15d, %r15d
	jle	.L4190
	cmpl	$6, 108(%rsp)
	jbe	.L4237
	vmovapd	.LC45(%rip), %zmm4
	movl	68(%rsp), %eax
	movl	%eax, %edx
	vmovapd	%zmm4, 256(%rsp)
	cmpl	%r15d, %eax
	je	.L4190
.L4132:
	movl	%r15d, %ecx
	subl	%edx, %ecx
	leal	-1(%rcx), %esi
	cmpl	$2, %esi
	jbe	.L4134
	vmovapd	.LC46(%rip), %ymm4
	vmovapd	%ymm4, 256(%rsp,%rdx,8)
	movl	%ecx, %edx
	andl	$-4, %edx
	addl	%edx, %eax
	cmpl	%ecx, %edx
	je	.L4190
.L4134:
	movq	.LC43(%rip), %rcx
	movslq	%eax, %rdx
	movq	%rcx, 256(%rsp,%rdx,8)
	leal	1(%rax), %edx
	cmpl	%r15d, %edx
	jge	.L4190
	movslq	%edx, %rdx
	addl	$2, %eax
	movq	%rcx, 256(%rsp,%rdx,8)
	cmpl	%eax, %r15d
	jle	.L4190
	cltq
	movq	%rcx, 256(%rsp,%rax,8)
.L4190:
	movq	120(%rsp), %rdi
	xorl	%r9d, %r9d
	movq	%r14, 144(%rsp)
	movq	96(%rsp), %rdx
	movq	%r9, %r14
	movl	32(%rsp), %r12d
	movl	68(%rsp), %esi
	movl	20(%rsp), %r8d
	movl	16(%rsp), %r10d
	movq	8(%rsp), %r11
	movq	%rdi, %r9
	jmp	.L4136
.L4229:
	movq	.LC43(%rip), %rax
	movl	$1, (%rdx)
	vmovq	%rax, %xmm0
	cmpl	$7, %r15d
	jle	.L4239
.L4390:
	vmovapd	256(%rsp), %zmm6
	vbroadcastsd	%xmm0, %zmm1
	vfnmadd132pd	(%r9), %zmm6, %zmm1
	vmovapd	%zmm1, 256(%rsp)
	cmpl	%r10d, %r8d
	je	.L4144
	movl	%r8d, %eax
	movl	%r8d, %ecx
.L4142:
	movl	%r10d, %edi
	subl	%eax, %edi
	leal	-1(%rdi), %r13d
	cmpl	$2, %r13d
	jbe	.L4145
	salq	$3, %rax
	vbroadcastsd	%xmm0, %ymm1
	leaq	(%rbx,%rax), %r13
	vmovapd	0(%r13), %ymm6
	vfnmadd132pd	(%r9,%rax), %ymm6, %ymm1
	movl	%edi, %eax
	andl	$-4, %eax
	addl	%eax, %ecx
	vmovapd	%ymm1, 0(%r13)
	cmpl	%edi, %eax
	je	.L4144
.L4145:
	movslq	%ecx, %rax
	leaq	(%r9,%rax,8), %rdi
	vmovsd	(%rdi), %xmm1
	vfnmadd213sd	256(%rsp,%rax,8), %xmm0, %xmm1
	vmovsd	%xmm1, 256(%rsp,%rax,8)
	leal	1(%rcx), %eax
	cmpl	%eax, %r15d
	jle	.L4144
	cltq
	vmovsd	8(%rdi), %xmm1
	addl	$2, %ecx
	vfnmadd213sd	256(%rsp,%rax,8), %xmm0, %xmm1
	vmovsd	%xmm1, 256(%rsp,%rax,8)
	cmpl	%ecx, %r15d
	jle	.L4144
	movslq	%ecx, %rcx
	vmovsd	256(%rsp,%rcx,8), %xmm6
	vfnmadd132sd	16(%rdi), %xmm6, %xmm0
	vmovsd	%xmm0, 256(%rsp,%rcx,8)
.L4144:
	addq	$4, %rdx
	addq	$64, %r9
	addq	$8, %r14
	cmpq	%r11, %rdx
	je	.L4388
.L4136:
	testl	%r15d, %r15d
	jle	.L4389
	cmpl	$6, 108(%rsp)
	jbe	.L4238
	vmovapd	(%r9), %zmm4
	vmulpd	192(%rsp), %zmm4, %zmm1
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vextractf64x2	$0x1, %ymm1, %xmm0
	vaddsd	%xmm8, %xmm1, %xmm3
	vextractf64x4	$0x1, %zmm1, %ymm1
	vaddsd	%xmm3, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm0, %xmm2
	vunpckhpd	%xmm0, %xmm0, %xmm0
	vaddsd	%xmm2, %xmm0, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vaddsd	%xmm0, %xmm1, %xmm0
	vextractf64x2	$0x1, %ymm1, %xmm1
	vaddsd	%xmm0, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm1, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm1, %xmm0, %xmm0
	cmpl	%r15d, %esi
	je	.L4138
	movl	%esi, %edi
	movl	%esi, %eax
.L4137:
	movl	%r15d, %ecx
	subl	%edi, %ecx
	leal	-1(%rcx), %r13d
	cmpl	$2, %r13d
	jbe	.L4139
	leaq	(%rdi,%r14), %r13
	vmovapd	1408(%rsp,%r13,8), %ymm1
	vmulpd	192(%rsp,%rdi,8), %ymm1, %ymm1
	movl	%ecx, %edi
	andl	$-4, %edi
	addl	%edi, %eax
	vaddsd	%xmm0, %xmm1, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vextractf64x2	$0x1, %ymm1, %xmm1
	vaddsd	%xmm0, %xmm2, %xmm2
	vaddsd	%xmm2, %xmm1, %xmm0
	vunpckhpd	%xmm1, %xmm1, %xmm1
	vaddsd	%xmm1, %xmm0, %xmm0
	cmpl	%ecx, %edi
	je	.L4138
.L4139:
	movslq	%eax, %rcx
	vmovsd	192(%rsp,%rcx,8), %xmm4
	leaq	(%r9,%rcx,8), %rdi
	leal	1(%rax), %ecx
	vfmadd231sd	(%rdi), %xmm4, %xmm0
	cmpl	%ecx, %r15d
	jle	.L4138
	movslq	%ecx, %rcx
	addl	$2, %eax
	vmovsd	192(%rsp,%rcx,8), %xmm6
	vfmadd231sd	8(%rdi), %xmm6, %xmm0
	cmpl	%eax, %r15d
	jle	.L4138
	vmovsd	16(%rdi), %xmm4
	cltq
	vfmadd231sd	192(%rsp,%rax,8), %xmm4, %xmm0
.L4138:
	vcomisd	%xmm8, %xmm0
	jnb	.L4229
	vcvtsi2sdl	%r12d, %xmm7, %xmm0
	movl	%r12d, (%rdx)
	vmulsd	.LC43(%rip), %xmm0, %xmm0
	cmpl	$7, %r15d
	jg	.L4390
.L4239:
	xorl	%eax, %eax
	xorl	%ecx, %ecx
	jmp	.L4142
.L4097:
	cmpb	$0, 36(%rsp)
	jne	.L4222
	movq	16(%rcx), %rbx
.L4095:
	movq	9656(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L4391
	leaq	-40(%rbp), %rsp
	vmovq	%rbx, %xmm0
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
.L4222:
	.cfi_restore_state
	movq	24(%rcx), %rbx
	jmp	.L4095
.L4388:
	movq	56(%rsp), %rdx
	vmovsd	256(%rsp), %xmm10
	movq	144(%rsp), %r14
	cmpq	%rbx, %rdx
	je	.L4240
	leaq	264(%rsp), %rax
	vmovsd	%xmm10, %xmm10, %xmm4
	cmpq	%rax, %rdx
	je	.L4149
	.p2align 4
	.p2align 3
.L4151:
	vmovsd	(%rax), %xmm0
	addq	$8, %rax
	vmaxsd	%xmm4, %xmm0, %xmm4
	cmpq	%rax, %rdx
	jne	.L4151
.L4149:
	testl	%r15d, %r15d
	jle	.L4243
.L4397:
	vaddsd	%xmm8, %xmm10, %xmm10
	cmpl	$1, %r15d
	je	.L4152
	vaddsd	264(%rsp), %xmm10, %xmm10
	cmpl	$2, %r15d
	je	.L4152
	vaddsd	272(%rsp), %xmm10, %xmm10
	cmpl	$3, %r15d
	je	.L4152
	vaddsd	280(%rsp), %xmm10, %xmm10
	cmpl	$4, %r15d
	je	.L4152
	vaddsd	288(%rsp), %xmm10, %xmm10
	cmpl	$5, %r15d
	je	.L4152
	vaddsd	296(%rsp), %xmm10, %xmm10
	cmpl	$6, %r15d
	je	.L4152
	vaddsd	304(%rsp), %xmm10, %xmm10
	cmpl	$7, %r15d
	je	.L4152
	vaddsd	312(%rsp), %xmm10, %xmm10
.L4152:
	movq	%rbx, %rdi
	movl	$3, 104(%rsp)
	movl	%r15d, %ebx
	.p2align 4
	.p2align 3
.L4154:
	movq	120(%rsp), %r15
	xorl	%eax, %eax
	movq	%r14, %r12
	movq	96(%rsp), %r13
	jmp	.L4170
	.p2align 4
	.p2align 3
.L4226:
	vsubsd	%xmm4, %xmm1, %xmm2
	vandpd	.LC5(%rip), %xmm2, %xmm2
	vcomisd	%xmm2, %xmm5
	jbe	.L4167
	vsubsd	%xmm5, %xmm10, %xmm2
	vcomisd	%xmm0, %xmm2
	ja	.L4392
.L4167:
	addq	$64, %r15
	addq	$4, %r13
	cmpq	%r12, %r15
	je	.L4393
.L4170:
	vsubsd	%xmm5, %xmm4, %xmm6
	testl	%ebx, %ebx
	jle	.L4155
	movl	0(%r13), %r14d
	vmovsd	(%r15), %xmm0
	vcvtsi2sdl	%r14d, %xmm7, %xmm2
	vfmadd213sd	256(%rsp), %xmm2, %xmm0
	vmaxsd	%xmm9, %xmm0, %xmm1
	vmovsd	%xmm0, 320(%rsp)
	vaddsd	%xmm8, %xmm0, %xmm0
	cmpl	$1, %ebx
	je	.L4157
	vmovsd	8(%r15), %xmm3
	vfmadd213sd	264(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 328(%rsp)
	cmpl	$2, %ebx
	je	.L4157
	vmovsd	16(%r15), %xmm3
	vfmadd213sd	272(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 336(%rsp)
	cmpl	$3, %ebx
	je	.L4157
	vmovsd	24(%r15), %xmm3
	vfmadd213sd	280(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 344(%rsp)
	cmpl	$4, %ebx
	je	.L4157
	vmovsd	32(%r15), %xmm3
	vfmadd213sd	288(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 352(%rsp)
	cmpl	$5, %ebx
	je	.L4157
	vmovsd	40(%r15), %xmm3
	vfmadd213sd	296(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 360(%rsp)
	cmpl	$6, %ebx
	je	.L4157
	vmovsd	48(%r15), %xmm3
	vfmadd213sd	304(%rsp), %xmm2, %xmm3
	vmaxsd	%xmm1, %xmm3, %xmm1
	vaddsd	%xmm3, %xmm0, %xmm0
	vmovsd	%xmm3, 368(%rsp)
	cmpl	$7, %ebx
	je	.L4157
	vmovsd	312(%rsp), %xmm3
	vfmadd132sd	56(%r15), %xmm3, %xmm2
	vmaxsd	%xmm1, %xmm2, %xmm1
	vaddsd	%xmm2, %xmm0, %xmm0
	vmovsd	%xmm2, 376(%rsp)
.L4157:
	vcomisd	%xmm1, %xmm6
	jbe	.L4226
.L4165:
	movq	128(%rsp), %rdx
	leaq	320(%rsp), %rsi
	vmovsd	%xmm0, 136(%rsp)
	vmovsd	%xmm1, 144(%rsp)
	vzeroupper
	call	memcpy@PLT
	vmovsd	144(%rsp), %xmm1
	vxorps	%xmm7, %xmm7, %xmm7
	vmovsd	136(%rsp), %xmm0
	movq	%rax, %rdi
	movq	.LC3(%rip), %rax
	vxorpd	%xmm8, %xmm8, %xmm8
	vmovq	%rax, %xmm9
	movq	.LC47(%rip), %rax
	vmovsd	%xmm1, %xmm1, %xmm4
	vmovsd	%xmm0, %xmm0, %xmm10
	vmovq	%rax, %xmm5
.L4166:
	negl	%r14d
	addq	$64, %r15
	movl	$1, %eax
	addq	$4, %r13
	movl	%r14d, -4(%r13)
	cmpq	%r12, %r15
	jne	.L4170
.L4393:
	movq	%r12, %r14
	testb	%al, %al
	je	.L4171
	decl	104(%rsp)
	jne	.L4154
.L4171:
	vmovsd	88(%rsp), %xmm6
	movl	%ebx, %r15d
	movq	%rdi, %rbx
	vcomisd	%xmm4, %xmm6
	jbe	.L4394
.L4172:
	movq	40(%rsp), %rdx
	movq	96(%rsp), %rsi
	vmovsd	%xmm10, 136(%rsp)
	vmovsd	%xmm4, 144(%rsp)
	movq	80(%rsp), %rdi
	vzeroupper
	call	memcpy@PLT
	movq	.LC47(%rip), %rax
	vxorpd	%xmm8, %xmm8, %xmm8
	vmovsd	136(%rsp), %xmm10
	vmovsd	144(%rsp), %xmm4
	vxorps	%xmm7, %xmm7, %xmm7
	vmovq	%rax, %xmm5
	movq	.LC3(%rip), %rax
	vmovq	%rax, %xmm9
	vmovsd	%xmm10, 48(%rsp)
	vmovsd	%xmm4, 88(%rsp)
.L4173:
	movq	56(%rsp), %rcx
	cmpq	%rbx, %rcx
	je	.L4253
.L4396:
	leaq	264(%rsp), %rax
	cmpq	%rax, %rcx
	je	.L4253
	movq	%rbx, %rdx
	.p2align 4
	.p2align 3
.L4178:
	vmovsd	(%rax), %xmm0
	vucomisd	(%rdx), %xmm0
	cmova	%rax, %rdx
	addq	$8, %rax
	cmpq	%rax, %rcx
	jne	.L4178
	subq	%rbx, %rdx
	sarq	$3, %rdx
.L4175:
	testl	%r15d, %r15d
	jle	.L4183
	cmpl	$6, 108(%rsp)
	jbe	.L4255
	vpbroadcastd	%edx, %ymm0
	vmovapd	192(%rsp), %ymm4
	vmovapd	224(%rsp), %ymm6
	vpcmpd	$0, .LC48(%rip), %ymm0, %k1
	movl	68(%rsp), %eax
	vmovapd	.LC49(%rip), %ymm1{%k1}{z}
	kshiftrb	$4, %k1, %k1
	vfmadd231pd	.LC50(%rip), %ymm4, %ymm1
	vmovapd	.LC49(%rip), %ymm0{%k1}{z}
	vfmadd231pd	.LC50(%rip), %ymm6, %ymm0
	movl	%eax, %ecx
	vmovapd	%ymm1, 192(%rsp)
	vmovapd	%ymm0, 224(%rsp)
	cmpl	%r15d, %eax
	je	.L4183
.L4181:
	movl	%r15d, %esi
	subl	%ecx, %esi
	leal	-1(%rsi), %edi
	cmpl	$2, %edi
	jbe	.L4184
	vpbroadcastd	%eax, %xmm0
	vpaddd	.LC51(%rip), %xmm0, %xmm0
	vpbroadcastd	%edx, %xmm1
	leaq	192(%rsp,%rcx,8), %rcx
	vmovapd	(%rcx), %xmm4
	vmovapd	16(%rcx), %xmm6
	vpcmpd	$0, %xmm1, %xmm0, %k1
	vmovapd	.LC52(%rip), %xmm1{%k1}{z}
	kshiftrb	$2, %k1, %k1
	vfmadd231pd	.LC53(%rip), %xmm4, %xmm1
	vmovapd	.LC52(%rip), %xmm0{%k1}{z}
	vfmadd231pd	.LC53(%rip), %xmm6, %xmm0
	vmovapd	%xmm1, (%rcx)
	vmovapd	%xmm0, 16(%rcx)
	movl	%esi, %ecx
	andl	$-4, %ecx
	addl	%ecx, %eax
	cmpl	%esi, %ecx
	je	.L4183
.L4184:
	movq	.LC44(%rip), %rsi
	vmovsd	.LC54(%rip), %xmm4
	movslq	%eax, %rcx
	vmulsd	192(%rsp,%rcx,8), %xmm4, %xmm1
	vmovq	%rsi, %xmm0
	cmpl	%edx, %eax
	je	.L4186
	vmovsd	%xmm8, %xmm8, %xmm0
.L4186:
	vaddsd	%xmm1, %xmm0, %xmm0
	vmovsd	%xmm0, 192(%rsp,%rcx,8)
	leal	1(%rax), %ecx
	cmpl	%ecx, %r15d
	jle	.L4183
	movq	.LC44(%rip), %rdi
	vmovsd	.LC54(%rip), %xmm6
	movslq	%ecx, %rsi
	vmulsd	192(%rsp,%rsi,8), %xmm6, %xmm0
	vmovq	%rdi, %xmm1
	cmpl	%edx, %ecx
	je	.L4187
	vmovsd	%xmm8, %xmm8, %xmm1
.L4187:
	vaddsd	%xmm1, %xmm0, %xmm0
	addl	$2, %eax
	vmovsd	%xmm0, 192(%rsp,%rsi,8)
	cmpl	%eax, %r15d
	jle	.L4183
	movq	.LC44(%rip), %rsi
	movslq	%eax, %rcx
	vmovsd	.LC54(%rip), %xmm4
	vmulsd	192(%rsp,%rcx,8), %xmm4, %xmm1
	vmovq	%rsi, %xmm0
	cmpl	%edx, %eax
	je	.L4188
	vmovsd	%xmm8, %xmm8, %xmm0
.L4188:
	vaddsd	%xmm1, %xmm0, %xmm0
	vmovsd	%xmm0, 192(%rsp,%rcx,8)
.L4183:
	cmpl	$1, 64(%rsp)
	je	.L4395
	movl	$1, 64(%rsp)
	jmp	.L4126
	.p2align 4
	.p2align 3
.L4155:
	vmovsd	%xmm9, %xmm9, %xmm1
	vmovsd	%xmm8, %xmm8, %xmm0
	vcomisd	%xmm9, %xmm6
	jbe	.L4226
	movl	0(%r13), %r14d
	vmovsd	%xmm9, %xmm9, %xmm4
	vmovsd	%xmm8, %xmm8, %xmm10
	jmp	.L4166
	.p2align 4
	.p2align 3
.L4392:
	movl	0(%r13), %r14d
	vmovsd	%xmm1, %xmm1, %xmm4
	vmovsd	%xmm0, %xmm0, %xmm10
	testl	%ebx, %ebx
	jg	.L4165
	jmp	.L4166
.L4389:
	movl	%r12d, (%rdx)
	jmp	.L4144
.L4238:
	xorl	%edi, %edi
	vmovsd	%xmm8, %xmm8, %xmm0
	xorl	%eax, %eax
	jmp	.L4137
.L4394:
	vucomisd	%xmm6, %xmm4
	jp	.L4173
	jne	.L4173
	vmovsd	48(%rsp), %xmm6
	vcomisd	%xmm10, %xmm6
	ja	.L4172
	movq	56(%rsp), %rcx
	cmpq	%rbx, %rcx
	jne	.L4396
.L4253:
	xorl	%edx, %edx
	jmp	.L4175
.L4240:
	vmovsd	%xmm10, %xmm10, %xmm4
	testl	%r15d, %r15d
	jg	.L4397
.L4243:
	vmovsd	%xmm8, %xmm8, %xmm10
	jmp	.L4152
.L4395:
	vpxor	%xmm0, %xmm0, %xmm0
	movq	120(%rsp), %rax
	vxorpd	%xmm1, %xmm1, %xmm1
	vmovdqa	%xmm0, 896(%rsp)
	vmovdqa	%xmm0, 912(%rsp)
	vmovdqa	%xmm0, 928(%rsp)
	vmovdqa	%xmm0, 944(%rsp)
	vbroadcastsd	.LC56(%rip), %zmm0
.L4191:
	vandpd	(%rax), %zmm0, %zmm2
	addq	$64, %rax
	vaddpd	%zmm2, %zmm1, %zmm1
	cmpq	%rax, %r14
	jne	.L4191
	movq	24(%rsp), %rdx
	movq	80(%rsp), %rax
	vmovapd	%ymm1, %ymm0
	vunpckhpd	%xmm1, %xmm1, %xmm2
	vmovapd	%zmm1, 896(%rsp)
	addq	%rax, %rdx
	cmpq	%rax, %rdx
	je	.L4192
	leaq	904(%rsp), %rax
	cmpq	%rax, %rdx
	jne	.L4195
	jmp	.L4192
	.p2align 4
	.p2align 3
.L4398:
	vmovsd	(%rax), %xmm2
.L4195:
	addq	$8, %rax
	vminsd	%xmm0, %xmm2, %xmm0
	cmpq	%rax, %rdx
	jne	.L4398
.L4192:
	vmovsd	72(%rsp), %xmm7
	movq	112(%rsp), %r15
	leaq	176(%rsp), %r13
	leaq	152(%rsp), %rsi
	movq	%r13, %rdx
	leaq	120(%r15), %rdi
	vsubsd	%xmm0, %xmm7, %xmm0
	vmulsd	.LC43(%rip), %xmm0, %xmm7
	vmovq	%xmm7, %rbx
	vmovsd	88(%rsp), %xmm7
	vmovq	%rbx, %xmm6
	vunpcklpd	%xmm6, %xmm7, %xmm0
	vmovapd	%xmm0, 176(%rsp)
	vzeroupper
	call	_ZNSt10_HashtableImSt4pairIKm10EvaluationESaIS3_ENSt8__detail10_Select1stESt8equal_toImESt4hashImENS5_18_Mod_range_hashingENS5_20_Default_ranged_hashENS5_20_Prime_rehash_policyENS5_17_Hashtable_traitsILb0ELb0ELb1EEEE10_M_emplaceIJRmS2_EEES0_INS5_14_Node_iteratorIS3_Lb0ELb0EEEbESt17integral_constantIbLb1EEDpOT_.isra.0
	movq	152(%rsp), %r14
	popcntq	%r14, %rax
	cmpl	8(%r15), %eax
	je	.L4399
.L4196:
	cmpb	$0, 36(%rsp)
	jne	.L4095
	movq	88(%rsp), %rbx
	jmp	.L4095
.L4237:
	xorl	%edx, %edx
	xorl	%eax, %eax
	jmp	.L4132
.L4255:
	xorl	%ecx, %ecx
	xorl	%eax, %eax
	jmp	.L4181
.L4384:
	call	_ZNSt6chrono3_V212steady_clock3nowEv@PLT
	movq	112(%rsp), %rcx
	cmpq	%rax, 2832(%rcx)
	jg	.L4101
	movb	$1, 2840(%rcx)
	jmp	.L4101
.L4399:
	movq	112(%rsp), %rax
	vmovsd	88(%rsp), %xmm7
	movq	%r14, 168(%rsp)
	vmovsd	2848(%rax), %xmm0
	vcomisd	%xmm7, %xmm0
	jbe	.L4197
	vmovsd	%xmm7, 2848(%rax)
	movq	%r14, 2856(%rax)
.L4197:
	movq	112(%rsp), %rax
	movq	208(%rax), %rdx
	movq	216(%rax), %rax
	movq	%rax, 144(%rsp)
	subq	%rdx, %rax
	cmpq	$1520, %rax
	jbe	.L4199
	vmovsd	(%rdx), %xmm0
	vmovq	%rbx, %xmm7
	vcomisd	%xmm7, %xmm0
	jbe	.L4200
.L4199:
	movq	112(%rsp), %r15
	movq	%r13, %rsi
	movq	%rbx, 176(%rsp)
	movq	%r14, 184(%rsp)
	leaq	208(%r15), %rdi
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	216(%r15), %r8
	movq	208(%r15), %rdi
	movq	%r8, %rsi
	vmovsd	-16(%r8), %xmm0
	movq	-8(%r8), %r10
	subq	%rdi, %rsi
	movq	%rsi, %rdx
	sarq	$4, %rdx
	leaq	-1(%rdx), %rax
	subq	$2, %rdx
	movq	%rdx, %rcx
	shrq	$63, %rcx
	addq	%rdx, %rcx
	sarq	%rcx
	testq	%rax, %rax
	jg	.L4205
	jmp	.L4400
	.p2align 4
	.p2align 3
.L4202:
	cmpq	8(%r9), %r10
	seta	%dl
.L4204:
	salq	$4, %rax
	addq	%rdi, %rax
	testb	%dl, %dl
	je	.L4206
	vmovdqu	(%r9), %xmm7
	vmovdqu	%xmm7, (%rax)
	leaq	-1(%rcx), %rax
	movq	%rax, %rdx
	shrq	$63, %rdx
	addq	%rax, %rdx
	movq	%rcx, %rax
	sarq	%rdx
	testq	%rcx, %rcx
	jle	.L4401
	movq	%rdx, %rcx
.L4205:
	movq	%rcx, %r9
	salq	$4, %r9
	addq	%rdi, %r9
	vmovsd	(%r9), %xmm1
	vucomisd	%xmm1, %xmm0
	jp	.L4267
	je	.L4202
.L4267:
	vcomisd	%xmm1, %xmm0
	seta	%dl
	jmp	.L4204
.L4232:
	vmovsd	.LC1(%rip), %xmm6
	movq	$4, 40(%rsp)
	movl	$1, %edi
	vmovsd	%xmm6, 72(%rsp)
	vmovsd	%xmm6, %xmm6, %xmm3
	jmp	.L4102
.L4387:
	leal	-1(%r15), %eax
	movl	%eax, 108(%rsp)
	jmp	.L4129
.L4400:
	leaq	-16(%rdi,%rsi), %rax
.L4206:
	vmovsd	%xmm0, (%rax)
	movq	%r10, 8(%rax)
	cmpq	$1536, %rsi
	ja	.L4402
.L4200:
	movq	112(%rsp), %rax
	movq	176(%rax), %rdx
	movq	184(%rax), %rax
	movq	%rax, 144(%rsp)
	subq	%rdx, %rax
	cmpq	$1520, %rax
	jbe	.L4209
	vmovsd	88(%rsp), %xmm7
	vcomisd	(%rdx), %xmm7
	jnb	.L4196
.L4209:
	movq	112(%rsp), %rcx
	movq	%r14, %rax
	xorl	%edx, %edx
	movq	248(%rcx), %rdi
	divq	%rdi
	movq	240(%rcx), %rax
	movq	(%rax,%rdx,8), %rax
	movq	%rdx, %r8
	testq	%rax, %rax
	je	.L4212
	movq	(%rax), %rcx
	movq	8(%rcx), %rsi
.L4214:
	cmpq	%rsi, %r14
	je	.L4196
	movq	(%rcx), %rcx
	testq	%rcx, %rcx
	je	.L4212
	movq	8(%rcx), %rsi
	xorl	%edx, %edx
	movq	%rsi, %rax
	divq	%rdi
	cmpq	%rdx, %r8
	je	.L4214
.L4212:
	vmovsd	88(%rsp), %xmm7
	movq	112(%rsp), %r15
	movq	%r13, %rsi
	movq	%r14, 184(%rsp)
	leaq	176(%r15), %rdi
	vmovsd	%xmm7, 176(%rsp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
	movq	184(%r15), %rax
	movq	176(%r15), %rdx
	vmovsd	-16(%rax), %xmm0
	movq	-8(%rax), %r8
	subq	%rdx, %rax
	movq	%rax, %rdi
	movq	%rax, %rcx
	sarq	$4, %rdi
	leaq	-1(%rdi), %rax
	subq	$2, %rdi
	movq	%rdi, %rsi
	shrq	$63, %rsi
	addq	%rdi, %rsi
	sarq	%rsi
	testq	%rax, %rax
	jg	.L4219
	jmp	.L4403
	.p2align 4
	.p2align 3
.L4216:
	cmpq	%r8, 8(%rdi)
	setb	%cl
.L4218:
	salq	$4, %rax
	addq	%rdx, %rax
	testb	%cl, %cl
	je	.L4220
	vmovdqu	(%rdi), %xmm7
	vmovdqu	%xmm7, (%rax)
	leaq	-1(%rsi), %rax
	movq	%rax, %rcx
	shrq	$63, %rcx
	addq	%rax, %rcx
	movq	%rsi, %rax
	sarq	%rcx
	testq	%rsi, %rsi
	jle	.L4404
	movq	%rcx, %rsi
.L4219:
	movq	%rsi, %rdi
	salq	$4, %rdi
	addq	%rdx, %rdi
	vmovsd	(%rdi), %xmm1
	vucomisd	%xmm0, %xmm1
	jp	.L4268
	je	.L4216
.L4268:
	vcomisd	%xmm1, %xmm0
	seta	%cl
	jmp	.L4218
.L4402:
	leaq	-16(%r8), %r15
	cmpq	$16, %rsi
	jg	.L4405
.L4208:
	movq	112(%rsp), %rax
	movq	%r15, 216(%rax)
	jmp	.L4200
.L4401:
	movq	%r9, %rax
	jmp	.L4206
.L4405:
	vmovdqu	(%rdi), %xmm7
	movq	-16(%r8), %rax
	movq	%r15, %rdx
	xorl	%esi, %esi
	movq	-8(%r8), %rcx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovq	%rax, %xmm0
	vmovdqu	%xmm7, -16(%r8)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	jmp	.L4208
.L4404:
	movq	%rdi, %rax
.L4220:
	movq	112(%rsp), %r15
	vmovsd	%xmm0, (%rax)
	movq	%r8, 8(%rax)
	leaq	168(%rsp), %rsi
	leaq	240(%r15), %r13
	movq	%r13, %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_insertIRKmNS1_10_AllocNodeISaINS1_10_Hash_nodeImLb0EEEEEEEESt4pairINS1_14_Node_iteratorImLb1ELb0EEEbEOT_RKT0_St17integral_constantIbLb1EE.constprop.0.isra.0
	movq	184(%r15), %rax
	movq	176(%r15), %rdx
	movq	%rax, 144(%rsp)
	subq	%rdx, %rax
	cmpq	$1536, %rax
	jbe	.L4196
	movq	8(%rdx), %rsi
	movq	%r13, %rdi
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE8_M_eraseESt17integral_constantIbLb1EERKm.isra.0
	movq	112(%rsp), %rcx
	movq	184(%rcx), %rax
	movq	176(%rcx), %rdi
	movq	%rax, %rdx
	leaq	-16(%rax), %r13
	subq	%rdi, %rdx
	cmpq	$16, %rdx
	jg	.L4406
.L4221:
	movq	112(%rsp), %rax
	movq	%r13, 184(%rax)
	jmp	.L4196
.L4403:
	leaq	-16(%rdx,%rcx), %rax
	jmp	.L4220
.L4406:
	vmovdqu	(%rdi), %xmm7
	movq	-16(%rax), %rdx
	xorl	%esi, %esi
	movq	-8(%rax), %rcx
	vmovq	%rdx, %xmm0
	movq	%r13, %rdx
	subq	%rdi, %rdx
	sarq	$4, %rdx
	vmovdqu	%xmm7, -16(%rax)
	call	_ZSt13__adjust_heapIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElS2_NS0_5__ops15_Iter_comp_iterISt4lessIS2_EEEEvT_T0_SE_T1_T2_.isra.0
	jmp	.L4221
	.p2align 4
	.p2align 3
.L4236:
	xorl	%edx, %edx
	xorl	%eax, %eax
	jmp	.L4127
.L4391:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE6002:
	.size	_ZN9Optimizer8evaluateEmb, .-_ZN9Optimizer8evaluateEmb
	.section	.text._ZN9Optimizer7descendE5Stateb,"axG",@progbits,_ZN9Optimizer7descendE5Stateb,comdat
	.align 2
	.p2align 4
	.weak	_ZN9Optimizer7descendE5Stateb
	.type	_ZN9Optimizer7descendE5Stateb, @function
_ZN9Optimizer7descendE5Stateb:
.LFB6133:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movq	%rdi, %r15
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rsi, %r12
	subq	$56, %rsp
	.cfi_def_cfa_offset 112
	movb	%dl, 23(%rsp)
	vmovsd	%xmm0, 32(%rsp)
	movl	$30, 44(%rsp)
.L4408:
	cmpb	$0, 2840(%r15)
	jne	.L4416
	testq	%r12, %r12
	je	.L4416
	vmovsd	32(%rsp), %xmm2
	movl	4(%r15), %edx
	movq	%r12, %rbx
	movq	%r12, 24(%rsp)
	.p2align 4
	.p2align 3
.L4415:
	movq	%r12, %rbp
	tzcntq	24(%rsp), %rax
	movl	%edx, 40(%rsp)
	btcq	%rax, %rbp
	testl	%edx, %edx
	jle	.L4409
	xorl	%r14d, %r14d
	.p2align 4
	.p2align 3
.L4414:
	btq	%r14, %r12
	jc	.L4410
	movzbl	23(%rsp), %edx
	movq	%rbp, %r13
	movq	%r15, %rdi
	vmovsd	%xmm2, 8(%rsp)
	btsq	%r14, %r13
	movq	%r13, %rsi
	call	_ZN9Optimizer8evaluateEmb
	vmovsd	8(%rsp), %xmm2
	vsubsd	.LC8(%rip), %xmm2, %xmm1
	vucomisd	%xmm0, %xmm1
	cmova	%r13, %rbx
	cmpb	$0, 2840(%r15)
	vcmpnltsd	%xmm1, %xmm0, %xmm1
	vblendvpd	%xmm1, %xmm2, %xmm0, %xmm2
	jne	.L4413
	movl	4(%r15), %edx
.L4410:
	incl	%r14d
	cmpl	%edx, %r14d
	jl	.L4414
	cmpb	$0, 2840(%r15)
	jne	.L4413
.L4409:
	blsr	24(%rsp), %rax
	movq	%rax, 24(%rsp)
	je	.L4413
	movl	40(%rsp), %eax
	testl	%eax, %eax
	jg	.L4415
.L4413:
	cmpq	%r12, %rbx
	je	.L4416
	decl	44(%rsp)
	movq	%rbx, %r12
	vmovsd	%xmm2, 32(%rsp)
	jne	.L4408
.L4416:
	vmovsd	32(%rsp), %xmm0
	addq	$56, %rsp
	.cfi_def_cfa_offset 56
	movq	%r12, %rax
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE6133:
	.size	_ZN9Optimizer7descendE5Stateb, .-_ZN9Optimizer7descendE5Stateb
	.section	.text._ZN9Optimizer11beam_searchEv,"axG",@progbits,_ZN9Optimizer11beam_searchEv,comdat
	.align 2
	.p2align 4
	.weak	_ZN9Optimizer11beam_searchEv
	.type	_ZN9Optimizer11beam_searchEv, @function
_ZN9Optimizer11beam_searchEv:
.LFB6004:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA6004
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movq	%rsi, %r14
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	xorl	%esi, %esi
	subq	$168, %rsp
	.cfi_def_cfa_offset 224
	movq	%rdi, 32(%rsp)
	movq	%r14, %rdi
	movq	%fs:40, %rax
	movq	%rax, 152(%rsp)
	xorl	%eax, %eax
.LEHB57:
	call	_ZN9Optimizer8evaluateEmb.constprop.0
.LEHE57:
	movq	32(%rsp), %r15
	movl	$16, %edi
	vmovq	%xmm0, %rbx
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqu	%xmm0, (%r15)
	movq	$0, 16(%r15)
.LEHB58:
	call	_Znwm@PLT
.LEHE58:
	movl	8(%r14), %ecx
	leaq	16(%rax), %rdx
	vmovq	%rax, %xmm4
	movq	%rbx, (%rax)
	vpinsrq	$1, %rdx, %xmm4, %xmm0
	movq	%rdx, 16(%r15)
	movq	$0, 8(%rax)
	movl	$1, 28(%rsp)
	vmovdqu	%xmm0, (%r15)
	testl	%ecx, %ecx
	jle	.L4426
.L4427:
	cmpb	$0, 2840(%r14)
	jne	.L4426
	leaq	144(%rsp), %rax
	vmovss	.LC37(%rip), %xmm4
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 80(%rsp)
	movq	%rax, 40(%rsp)
	movq	%rax, 96(%rsp)
	movq	32(%rsp), %rax
	vmovdqa	%xmm0, 64(%rsp)
	movq	$1, 104(%rsp)
	movq	$0, 112(%rsp)
	movq	$0, 120(%rsp)
	movq	$0, 136(%rsp)
	movq	$0, 144(%rsp)
	movq	(%rax), %r13
	movq	8(%rax), %rax
	vmovss	%xmm4, 128(%rsp)
	movq	%rax, 16(%rsp)
	cmpq	%rax, %r13
	je	.L4580
	movl	4(%r14), %eax
	addq	$16, %r13
	.p2align 4
	.p2align 3
.L4445:
	movl	%eax, 24(%rsp)
	xorl	%ebx, %ebx
	testl	%eax, %eax
	jle	.L4446
	.p2align 4
	.p2align 3
.L4444:
	movq	-8(%r13), %r12
	btq	%rbx, %r12
	jc	.L4432
	movq	104(%rsp), %rdi
	btsq	%rbx, %r12
	xorl	%edx, %edx
	movq	%r12, %rax
	divq	%rdi
	movq	96(%rsp), %rax
	leaq	0(,%rdx,8), %rbp
	movq	%rdx, %r8
	movq	(%rax,%rbp), %rax
	testq	%rax, %rax
	je	.L4433
	movq	(%rax), %rcx
	movq	8(%rcx), %rsi
.L4435:
	cmpq	%rsi, %r12
	je	.L4510
	movq	(%rcx), %rcx
	testq	%rcx, %rcx
	je	.L4433
	movq	8(%rcx), %rsi
	xorl	%edx, %edx
	movq	%rsi, %rax
	divq	%rdi
	cmpq	%rdx, %r8
	je	.L4435
.L4433:
	movl	$16, %edi
.LEHB59:
	call	_Znwm@PLT
.LEHE59:
	movq	%rax, %r15
	movq	$0, (%rax)
	movq	%r12, 8(%rax)
	movq	136(%rsp), %rax
	leaq	128(%rsp), %rdi
	movl	$1, %ecx
	movq	120(%rsp), %rdx
	movq	104(%rsp), %rsi
	movq	%rax, 48(%rsp)
	leaq	96(%rsp), %rax
	movq	%rax, 8(%rsp)
.LEHB60:
	call	_ZNKSt8__detail20_Prime_rehash_policy14_M_need_rehashEmmm@PLT
.LEHE60:
	movq	%rdx, %rsi
	testb	%al, %al
	jne	.L4581
.L4436:
	movq	96(%rsp), %rcx
	addq	%rcx, %rbp
	movq	0(%rbp), %rax
	testq	%rax, %rax
	je	.L4437
	movq	(%rax), %rax
	movq	%rax, (%r15)
	movq	0(%rbp), %rax
	movq	%r15, (%rax)
.L4438:
	movq	%r12, %rsi
	movq	%r14, %rdi
	incq	120(%rsp)
.LEHB61:
	call	_ZN9Optimizer8evaluateEmb.constprop.0
	leaq	48(%rsp), %rsi
	leaq	64(%rsp), %rdi
	vmovsd	%xmm0, 48(%rsp)
	movq	%r12, 56(%rsp)
	call	_ZNSt6vectorI5StateSaIS0_EE12emplace_backIJS0_EEERS0_DpOT_.isra.0
.LEHE61:
.L4510:
	cmpb	$0, 2840(%r14)
	jne	.L4443
	movl	4(%r14), %eax
.L4432:
	incl	%ebx
	cmpl	%eax, %ebx
	jl	.L4444
	cmpb	$0, 2840(%r14)
	jne	.L4443
.L4446:
	cmpq	%r13, 16(%rsp)
	je	.L4443
	movl	24(%rsp), %edx
	addq	$16, %r13
	testl	%edx, %edx
	jg	.L4445
.L4443:
	movq	72(%rsp), %r12
	movq	64(%rsp), %r13
	movl	$4096, %eax
	movl	$16384, %ebx
	movl	$256, %ecx
	movq	%r12, %r15
	subq	%r13, %r15
	movq	%r15, %rdx
	sarq	$4, %rdx
	cmpl	$3, 28(%rsp)
	movq	%rdx, %rsi
	cmovge	%rax, %rbx
	movl	$1024, %eax
	cmovge	%rcx, %rax
	cmpq	%rdx, %rax
	jnb	.L4448
	addq	%r13, %rbx
	cmpq	%r13, %r12
	je	.L4449
	cmpq	%r12, %rbx
	je	.L4509
	movq	%r13, %rbp
	cmpq	$48, %r15
	jle	.L4452
	vmovsd	0(%r13), %xmm1
	lzcntq	%rdx, %rdx
	movl	$63, %esi
	movq	%r15, %rdi
	subl	%edx, %esi
	movslq	%esi, %rsi
	addq	%rsi, %rsi
	.p2align 4
	.p2align 3
.L4453:
	sarq	$5, %rdi
	vmovsd	16(%rbp), %xmm2
	decq	%rsi
	leaq	16(%rbp), %rdx
	salq	$4, %rdi
	addq	%rbp, %rdi
	vmovsd	(%rdi), %xmm3
	vucomisd	%xmm3, %xmm2
	jp	.L4529
	jne	.L4529
	movq	8(%rdi), %rax
	cmpq	%rax, 24(%rbp)
	setb	%al
.L4457:
	vmovsd	-16(%r12), %xmm0
	testb	%al, %al
	je	.L4582
	vucomisd	%xmm0, %xmm3
	jp	.L4530
	jne	.L4530
	movq	-8(%r12), %rax
	cmpq	%rax, 8(%rdi)
	setb	%al
.L4460:
	movq	8(%rbp), %rcx
	testb	%al, %al
	jne	.L4472
	vucomisd	%xmm0, %xmm2
	jp	.L4531
	jne	.L4531
	movq	-8(%r12), %rax
	cmpq	%rax, 24(%rbp)
	jb	.L4464
.L4515:
	vmovdqu	16(%rbp), %xmm5
	vmovsd	%xmm1, 16(%rbp)
	movq	%rcx, 24(%rbp)
	vmovdqu	%xmm5, 0(%rbp)
.L4461:
	movq	%r12, %rcx
	.p2align 4
	.p2align 3
.L4485:
	vmovsd	0(%rbp), %xmm0
	jmp	.L4473
	.p2align 4
	.p2align 3
.L4474:
	movq	8(%rbp), %rax
	cmpq	%rax, 8(%rdx)
	jnb	.L4477
.L4476:
	vmovsd	16(%rdx), %xmm1
	addq	$16, %rdx
.L4473:
	vucomisd	%xmm1, %xmm0
	jp	.L4534
	je	.L4474
.L4534:
	vcomisd	%xmm1, %xmm0
	ja	.L4476
.L4477:
	leaq	-16(%rcx), %rax
	.p2align 4
	.p2align 3
.L4512:
	vmovsd	(%rax), %xmm2
	movq	%rax, %rcx
	vucomisd	%xmm2, %xmm0
	jp	.L4535
	jne	.L4535
	movq	8(%rcx), %rdi
	subq	$16, %rax
	cmpq	%rdi, 8(%rbp)
	jb	.L4512
.L4481:
	cmpq	%rcx, %rdx
	jnb	.L4583
	vmovdqu	(%rcx), %xmm6
	movq	8(%rdx), %rax
	addq	$16, %rdx
	vmovdqu	%xmm6, -16(%rdx)
	vmovsd	%xmm1, (%rcx)
	movq	%rax, 8(%rcx)
	vmovsd	(%rdx), %xmm1
	jmp	.L4485
	.p2align 4
	.p2align 3
.L4581:
	leaq	96(%rsp), %rax
	leaq	48(%rsp), %rdx
	movq	%rax, %rdi
	movq	%rax, 8(%rsp)
.LEHB62:
	call	_ZNSt10_HashtableImmSaImENSt8__detail9_IdentityESt8equal_toImESt4hashImENS1_18_Mod_range_hashingENS1_20_Default_ranged_hashENS1_20_Prime_rehash_policyENS1_17_Hashtable_traitsILb0ELb1ELb1EEEE9_M_rehashEmRKm
.LEHE62:
	movq	%r12, %rax
	xorl	%edx, %edx
	divq	104(%rsp)
	leaq	0(,%rdx,8), %rbp
	jmp	.L4436
	.p2align 4
	.p2align 3
.L4437:
	movq	112(%rsp), %rax
	movq	%r15, 112(%rsp)
	movq	%rax, (%r15)
	testq	%rax, %rax
	je	.L4439
	movq	8(%rax), %rax
	xorl	%edx, %edx
	divq	104(%rsp)
	movq	%r15, (%rcx,%rdx,8)
.L4439:
	leaq	112(%rsp), %rax
	movq	%rax, 0(%rbp)
	jmp	.L4438
	.p2align 4
	.p2align 3
.L4583:
	cmpq	%rdx, %rbx
	jb	.L4584
	movq	%rdx, %rbp
	movq	%r12, %rdi
	subq	%rbp, %rdi
	cmpq	$48, %rdi
	jle	.L4452
.L4486:
	testq	%rsi, %rsi
	jne	.L4453
	leaq	16(%rbx), %rsi
	movq	%r12, %rdx
	movq	%rbp, %rdi
	call	_ZSt13__heap_selectIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_SA_T0_
	vmovsd	0(%rbp), %xmm0
	vmovdqu	(%rbx), %xmm5
	movq	8(%rbp), %rax
	vmovdqu	%xmm5, 0(%rbp)
	vmovsd	%xmm0, (%rbx)
	movq	%rax, 8(%rbx)
.L4511:
	movq	%rbx, 72(%rsp)
	movq	%rbx, %r12
.L4448:
	movq	%r12, %r15
	subq	%r13, %r15
	movq	%r15, %rsi
	sarq	$4, %rsi
	cmpq	%r13, %r12
	je	.L4519
.L4509:
	lzcntq	%rsi, %rsi
	movl	$63, %edx
	movq	%r13, %rdi
	subl	%esi, %edx
	movq	%r12, %rsi
	movslq	%edx, %rdx
	addq	%rdx, %rdx
	call	_ZSt16__introsort_loopIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEElNS0_5__ops15_Iter_less_iterEEvT_SA_T0_T1_.isra.0
	cmpq	$256, %r15
	jle	.L4489
	leaq	256(%r13), %rbx
	movq	%r13, %rdi
	movq	%rbx, %rsi
	call	_ZSt16__insertion_sortIN9__gnu_cxx17__normal_iteratorIP5StateSt6vectorIS2_SaIS2_EEEENS0_5__ops15_Iter_less_iterEEvT_SA_T0_.isra.0
	movq	%rbx, %rsi
	cmpq	%rbx, %r12
	je	.L4488
	.p2align 4
	.p2align 3
.L4497:
	vmovsd	(%rsi), %xmm1
	movq	8(%rsi), %rcx
	movq	%rsi, %rax
	jmp	.L4492
	.p2align 4
	.p2align 3
.L4493:
	subq	$16, %rax
	cmpq	-8(%rdx), %rcx
	jnb	.L4496
.L4495:
	vmovdqu	(%rax), %xmm7
	vmovdqu	%xmm7, 16(%rax)
.L4492:
	vmovsd	-16(%rax), %xmm0
	movq	%rax, %rdx
	vucomisd	%xmm0, %xmm1
	jp	.L4536
	je	.L4493
.L4536:
	subq	$16, %rax
	vcomisd	%xmm1, %xmm0
	ja	.L4495
.L4496:
	addq	$16, %rsi
	vmovsd	%xmm1, (%rdx)
	movq	%rcx, 8(%rdx)
	cmpq	%rsi, %r12
	jne	.L4497
	jmp	.L4488
.L4580:
	xorl	%r12d, %r12d
	xorl	%r13d, %r13d
	cmpl	$2, 28(%rsp)
	jg	.L4488
.L4519:
	movq	%r12, %r13
.L4488:
	movq	32(%rsp), %rbx
	movq	80(%rsp), %rax
	vmovq	%r13, %xmm5
	movq	$0, 80(%rsp)
	vpinsrq	$1, %r12, %xmm5, %xmm0
	movq	(%rbx), %rdi
	vmovdqu	%xmm0, (%rbx)
	vpxor	%xmm0, %xmm0, %xmm0
	movq	16(%rbx), %rsi
	vmovdqa	%xmm0, 64(%rsp)
	movq	%rax, 16(%rbx)
	testq	%rdi, %rdi
	je	.L4499
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L4499:
	movq	112(%rsp), %rbx
	testq	%rbx, %rbx
	je	.L4503
	.p2align 4
	.p2align 3
.L4500:
	movq	%rbx, %rdi
	movq	(%rbx), %rbx
	movl	$16, %esi
	call	_ZdlPvm@PLT
	testq	%rbx, %rbx
	jne	.L4500
.L4503:
	movq	104(%rsp), %rax
	movq	96(%rsp), %rdi
	xorl	%esi, %esi
	leaq	0(,%rax,8), %rdx
	call	memset@PLT
	movq	104(%rsp), %rsi
	movq	$0, 120(%rsp)
	movq	$0, 112(%rsp)
	movq	96(%rsp), %rdi
	cmpq	40(%rsp), %rdi
	je	.L4585
	salq	$3, %rsi
	call	_ZdlPvm@PLT
	incl	28(%rsp)
	movl	28(%rsp), %eax
	cmpl	8(%r14), %eax
	jle	.L4427
.L4426:
	movq	152(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L4586
	movq	32(%rsp), %rax
	addq	$168, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
.L4531:
	.cfi_restore_state
	vcomisd	%xmm2, %xmm0
	jbe	.L4515
.L4464:
	vmovdqu	-16(%r12), %xmm5
	vmovdqu	%xmm5, 0(%rbp)
	vmovsd	%xmm1, -16(%r12)
	movq	%rcx, -8(%r12)
	vmovsd	16(%rbp), %xmm1
	jmp	.L4461
	.p2align 4
	.p2align 3
.L4535:
	subq	$16, %rax
	vcomisd	%xmm0, %xmm2
	ja	.L4512
	jm
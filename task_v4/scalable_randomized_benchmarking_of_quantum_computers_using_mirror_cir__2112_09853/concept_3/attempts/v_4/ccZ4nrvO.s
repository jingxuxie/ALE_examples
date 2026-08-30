	.file	"delete.cpp"
	.text
	.section	.text._ZNKSt5ctypeIcE8do_widenEc,"axG",@progbits,_ZNKSt5ctypeIcE8do_widenEc,comdat
	.align 2
	.p2align 4
	.weak	_ZNKSt5ctypeIcE8do_widenEc
	.type	_ZNKSt5ctypeIcE8do_widenEc, @function
_ZNKSt5ctypeIcE8do_widenEc:
.LFB3705:
	.cfi_startproc
	endbr64
	movl	%esi, %eax
	ret
	.cfi_endproc
.LFE3705:
	.size	_ZNKSt5ctypeIcE8do_widenEc, .-_ZNKSt5ctypeIcE8do_widenEc
	.section	.text._ZNSt6vectorISt4pairIiiESaIS1_EED2Ev,"axG",@progbits,_ZNSt6vectorISt4pairIiiESaIS1_EED5Ev,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorISt4pairIiiESaIS1_EED2Ev
	.type	_ZNSt6vectorISt4pairIiiESaIS1_EED2Ev, @function
_ZNSt6vectorISt4pairIiiESaIS1_EED2Ev:
.LFB6248:
	.cfi_startproc
	endbr64
	movq	(%rdi), %r8
	testq	%r8, %r8
	je	.L5
	movq	16(%rdi), %rsi
	movq	%r8, %rdi
	subq	%r8, %rsi
	jmp	_ZdlPvm@PLT
	.p2align 4
	.p2align 3
.L5:
	ret
	.cfi_endproc
.LFE6248:
	.size	_ZNSt6vectorISt4pairIiiESaIS1_EED2Ev, .-_ZNSt6vectorISt4pairIiiESaIS1_EED2Ev
	.weak	_ZNSt6vectorISt4pairIiiESaIS1_EED1Ev
	.set	_ZNSt6vectorISt4pairIiiESaIS1_EED1Ev,_ZNSt6vectorISt4pairIiiESaIS1_EED2Ev
	.text
	.p2align 4
	.type	__tcf_0, @function
__tcf_0:
.LFB7516:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	leaq	192+_ZL5words(%rip), %rbx
	subq	$8, %rsp
	.cfi_def_cfa_offset 32
	leaq	-192(%rbx), %rbp
	.p2align 4
	.p2align 3
.L10:
	movq	-32(%rbx), %rdi
	subq	$32, %rbx
	leaq	16(%rbx), %rax
	cmpq	%rax, %rdi
	je	.L7
	movq	16(%rbx), %rax
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
	cmpq	%rbp, %rbx
	jne	.L10
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L7:
	.cfi_restore_state
	cmpq	%rbp, %rbx
	jne	.L10
	addq	$8, %rsp
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE7516:
	.size	__tcf_0, .-__tcf_0
	.section	.text._ZNSt6vectorISt5arrayIiLm3EESaIS1_EED2Ev,"axG",@progbits,_ZNSt6vectorISt5arrayIiLm3EESaIS1_EED5Ev,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EED2Ev
	.type	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EED2Ev, @function
_ZNSt6vectorISt5arrayIiLm3EESaIS1_EED2Ev:
.LFB7518:
	.cfi_startproc
	endbr64
	movq	(%rdi), %r8
	testq	%r8, %r8
	je	.L15
	movq	16(%rdi), %rsi
	movq	%r8, %rdi
	subq	%r8, %rsi
	jmp	_ZdlPvm@PLT
	.p2align 4
	.p2align 3
.L15:
	ret
	.cfi_endproc
.LFE7518:
	.size	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EED2Ev, .-_ZNSt6vectorISt5arrayIiLm3EESaIS1_EED2Ev
	.weak	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EED1Ev
	.set	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EED1Ev,_ZNSt6vectorISt5arrayIiLm3EESaIS1_EED2Ev
	.section	.rodata.str1.8,"aMS",@progbits,1
	.align 8
.LC0:
	.string	"basic_string::_M_construct null not valid"
	.text
	.align 2
	.p2align 4
	.type	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEC2IS3_EEPKcRKS3_.constprop.0, @function
_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEC2IS3_EEPKcRKS3_.constprop.0:
.LFB7529:
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
	leaq	16(%rdi), %r13
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	subq	$24, %rsp
	.cfi_def_cfa_offset 64
	movq	%fs:40, %rax
	movq	%rax, 8(%rsp)
	xorl	%eax, %eax
	movq	%r13, (%rdi)
	testq	%rsi, %rsi
	je	.L17
	movq	%rdi, %rbx
	movq	%rsi, %rdi
	movq	%rsi, %rbp
	call	strlen@PLT
	movq	%rax, %r12
	movq	%rax, (%rsp)
	cmpq	$15, %rax
	ja	.L30
	cmpq	$1, %rax
	jne	.L21
	movzbl	0(%rbp), %eax
	movb	%al, 16(%rbx)
.L22:
	movq	(%rsp), %rax
	movq	(%rbx), %rdx
	movq	%rax, 8(%rbx)
	movb	$0, (%rdx,%rax)
	movq	8(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L31
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
.L21:
	.cfi_restore_state
	testq	%rax, %rax
	je	.L22
	jmp	.L20
.L30:
	movq	%rsp, %rsi
	xorl	%edx, %edx
	movq	%rbx, %rdi
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_createERmm@PLT
	movq	%rax, %r13
	movq	%rax, (%rbx)
	movq	(%rsp), %rax
	movq	%rax, 16(%rbx)
.L20:
	movq	%r12, %rdx
	movq	%rbp, %rsi
	movq	%r13, %rdi
	call	memcpy@PLT
	jmp	.L22
.L31:
	call	__stack_chk_fail@PLT
.L17:
	leaq	.LC0(%rip), %rdi
	call	_ZSt19__throw_logic_errorPKc@PLT
	.cfi_endproc
.LFE7529:
	.size	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEC2IS3_EEPKcRKS3_.constprop.0, .-_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEC2IS3_EEPKcRKS3_.constprop.0
	.align 2
	.p2align 4
	.type	_ZNSt6vectorISt4pairIiiESaIS1_EEaSERKS3_.isra.0, @function
_ZNSt6vectorISt4pairIiiESaIS1_EEaSERKS3_.isra.0:
.LFB7532:
	.cfi_startproc
	cmpq	%rdi, %rsi
	je	.L106
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	.cfi_offset 15, -24
	.cfi_offset 14, -32
	.cfi_offset 13, -40
	.cfi_offset 12, -48
	movq	%rdi, %r12
	pushq	%rbx
	movq	8(%rsi), %r15
	.cfi_offset 3, -56
	movq	(%rsi), %rbx
	andq	$-64, %rsp
	movq	(%rdi), %rdi
	movq	16(%r12), %rsi
	movq	%r15, %r14
	subq	%rbx, %r14
	subq	%rdi, %rsi
	cmpq	%rsi, %r14
	jbe	.L34
	testq	%r14, %r14
	je	.L65
	movabsq	$9223372036854775800, %rax
	cmpq	%rax, %r14
	ja	.L109
	movq	%r14, %rdi
	call	_Znwm@PLT
	movq	(%r12), %rdi
	movq	16(%r12), %rsi
	movq	%rax, %r13
	subq	%rdi, %rsi
.L35:
	movq	%r15, %rcx
	xorl	%edx, %edx
	subq	%rbx, %rcx
	cmpq	%rbx, %r15
	je	.L42
	.p2align 4
	.p2align 3
.L41:
	movq	(%rbx,%rdx), %rax
	movq	%rax, 0(%r13,%rdx)
	addq	$8, %rdx
	cmpq	%rcx, %rdx
	jne	.L41
.L42:
	testq	%rdi, %rdi
	je	.L40
	call	_ZdlPvm@PLT
.L40:
	movq	%r13, (%r12)
	addq	%r14, %r13
	movq	%r13, 16(%r12)
.L43:
	movq	%r13, 8(%r12)
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
.L34:
	.cfi_restore_state
	movq	8(%r12), %rcx
	leaq	(%rdi,%r14), %r13
	movq	%rcx, %r9
	subq	%rdi, %r9
	cmpq	%r9, %r14
	ja	.L44
	testq	%r14, %r14
	jle	.L43
	leaq	8(%rbx), %rax
	movq	%rdi, %rsi
	movq	%r14, %rcx
	subq	%rax, %rsi
	sarq	$3, %rcx
	addq	$4, %rsi
	movq	%rcx, %rdx
	cmpq	$56, %rsi
	jbe	.L88
	cmpq	$24, %r14
	jle	.L88
	cmpq	$56, %r14
	jle	.L66
	shrq	$3, %rdx
	xorl	%eax, %eax
	salq	$6, %rdx
	.p2align 4
	.p2align 3
.L47:
	vmovdqu32	(%rbx,%rax), %zmm0
	vmovdqu32	%zmm0, (%rdi,%rax)
	addq	$64, %rax
	cmpq	%rax, %rdx
	jne	.L47
	movq	%rcx, %rax
	movq	%rcx, %rdx
	andq	$-8, %rax
	leaq	0(,%rax,8), %rsi
	subq	%rax, %rdx
	leaq	(%rbx,%rsi), %r8
	addq	%rdi, %rsi
	cmpq	%rax, %rcx
	je	.L100
.L46:
	subq	%rax, %rcx
	leaq	-1(%rcx), %r9
	cmpq	$2, %r9
	jbe	.L50
	salq	$3, %rax
	vmovdqu	(%rbx,%rax), %ymm2
	vmovdqu	%ymm2, (%rdi,%rax)
	movq	%rcx, %rax
	andq	$-4, %rax
	leaq	0(,%rax,8), %rdi
	subq	%rax, %rdx
	addq	%rdi, %r8
	addq	%rdi, %rsi
	cmpq	%rax, %rcx
	je	.L100
.L50:
	movq	(%r8), %rax
	movq	%rax, (%rsi)
	cmpq	$1, %rdx
	je	.L100
	movq	8(%r8), %rax
	movq	%rax, 8(%rsi)
	cmpq	$2, %rdx
	je	.L100
	movq	16(%r8), %rax
	movq	%rax, 16(%rsi)
	vzeroupper
	jmp	.L43
	.p2align 4
	.p2align 3
.L106:
	.cfi_def_cfa 7, 8
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L44:
	.cfi_def_cfa 6, 16
	.cfi_offset 3, -56
	.cfi_offset 6, -16
	.cfi_offset 12, -48
	.cfi_offset 13, -40
	.cfi_offset 14, -32
	.cfi_offset 15, -24
	leaq	(%rbx,%r9), %rsi
	testq	%r9, %r9
	jle	.L59
	leaq	8(%rbx), %rax
	movq	%rdi, %r10
	movq	%r9, %r8
	subq	%rax, %r10
	sarq	$3, %r8
	addq	$4, %r10
	movq	%r8, %rdx
	cmpq	$56, %r10
	jbe	.L89
	cmpq	$24, %r9
	jle	.L89
	cmpq	$56, %r9
	jle	.L67
	shrq	$3, %rdx
	xorl	%eax, %eax
	salq	$6, %rdx
	.p2align 4
	.p2align 3
.L57:
	vmovdqu32	(%rbx,%rax), %zmm1
	vmovdqu32	%zmm1, (%rdi,%rax)
	addq	$64, %rax
	cmpq	%rax, %rdx
	jne	.L57
	movq	%r8, %rax
	movq	%r8, %rdx
	andq	$-8, %rax
	leaq	0(,%rax,8), %r9
	subq	%rax, %rdx
	leaq	(%rbx,%r9), %r10
	addq	%rdi, %r9
	cmpq	%rax, %r8
	je	.L103
.L56:
	subq	%rax, %r8
	leaq	-1(%r8), %r11
	cmpq	$2, %r11
	jbe	.L61
	salq	$3, %rax
	vmovdqu	(%rbx,%rax), %ymm3
	vmovdqu	%ymm3, (%rdi,%rax)
	movq	%r8, %rax
	andq	$-4, %rax
	leaq	0(,%rax,8), %rdi
	subq	%rax, %rdx
	addq	%rdi, %r10
	addq	%rdi, %r9
	cmpq	%rax, %r8
	je	.L103
.L61:
	movq	(%r10), %rax
	movq	%rax, (%r9)
	cmpq	$1, %rdx
	je	.L103
	movq	8(%r10), %rax
	movq	%rax, 8(%r9)
	cmpq	$2, %rdx
	je	.L103
	movq	16(%r10), %rax
	movq	%rax, 16(%r9)
	vzeroupper
.L59:
	movq	%r15, %rdi
	xorl	%edx, %edx
	subq	%rsi, %rdi
	cmpq	%rsi, %r15
	je	.L43
	.p2align 4
	.p2align 3
.L64:
	movq	(%rsi,%rdx), %rax
	movq	%rax, (%rcx,%rdx)
	addq	$8, %rdx
	cmpq	%rdx, %rdi
	jne	.L64
	jmp	.L43
	.p2align 4
	.p2align 3
.L110:
	addq	$8, %rax
.L89:
	movq	(%rbx), %r8
	addq	$8, %rdi
	movq	%rax, %rbx
	movq	%r8, -8(%rdi)
	decq	%rdx
	jne	.L110
	jmp	.L59
	.p2align 4
	.p2align 3
.L111:
	addq	$8, %rax
.L88:
	movq	(%rbx), %rcx
	addq	$8, %rdi
	movq	%rax, %rbx
	movq	%rcx, -8(%rdi)
	decq	%rdx
	jne	.L111
	jmp	.L43
	.p2align 4
	.p2align 3
.L65:
	xorl	%r13d, %r13d
	jmp	.L35
	.p2align 4
	.p2align 3
.L103:
	vzeroupper
	jmp	.L59
	.p2align 4
	.p2align 3
.L100:
	vzeroupper
	jmp	.L43
.L109:
	testq	%r14, %r14
	jns	.L37
	call	_ZSt28__throw_bad_array_new_lengthv@PLT
.L66:
	movq	%rdi, %rsi
	movq	%rbx, %r8
	xorl	%eax, %eax
	jmp	.L46
.L67:
	movq	%rdi, %r9
	movq	%rbx, %r10
	xorl	%eax, %eax
	jmp	.L56
.L37:
	call	_ZSt17__throw_bad_allocv@PLT
	.cfi_endproc
.LFE7532:
	.size	_ZNSt6vectorISt4pairIiiESaIS1_EEaSERKS3_.isra.0, .-_ZNSt6vectorISt4pairIiiESaIS1_EEaSERKS3_.isra.0
	.p2align 4
	.type	_ZSt4endlIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_.isra.0, @function
_ZSt4endlIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_.isra.0:
.LFB7534:
	.cfi_startproc
	pushq	%r12
	.cfi_def_cfa_offset 16
	.cfi_offset 12, -16
	pushq	%rbp
	.cfi_def_cfa_offset 24
	.cfi_offset 6, -24
	subq	$8, %rsp
	.cfi_def_cfa_offset 32
	movq	(%rdi), %rax
	movq	-24(%rax), %rax
	movq	240(%rdi,%rax), %r12
	testq	%r12, %r12
	je	.L118
	cmpb	$0, 56(%r12)
	movq	%rdi, %rbp
	je	.L114
	movzbl	67(%r12), %eax
.L115:
	movq	%rbp, %rdi
	movsbl	%al, %esi
	call	_ZNSo3putEc@PLT
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	movq	%rax, %rdi
	jmp	_ZNSo5flushEv@PLT
.L114:
	.cfi_restore_state
	movq	%r12, %rdi
	call	_ZNKSt5ctypeIcE13_M_widen_initEv@PLT
	movq	(%r12), %rax
	leaq	_ZNKSt5ctypeIcE8do_widenEc(%rip), %rcx
	movq	48(%rax), %rdx
	movl	$10, %eax
	cmpq	%rcx, %rdx
	je	.L115
	movl	$10, %esi
	movq	%r12, %rdi
	call	*%rdx
	jmp	.L115
.L118:
	call	_ZSt16__throw_bad_castv@PLT
	.cfi_endproc
.LFE7534:
	.size	_ZSt4endlIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_.isra.0, .-_ZSt4endlIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_.isra.0
	.align 2
	.p2align 4
	.type	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE12_M_constructIPcEEvT_S7_St20forward_iterator_tag.constprop.0, @function
_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE12_M_constructIPcEEvT_S7_St20forward_iterator_tag.constprop.0:
.LFB7537:
	.cfi_startproc
	pushq	%r12
	.cfi_def_cfa_offset 16
	.cfi_offset 12, -16
	pushq	%rbp
	.cfi_def_cfa_offset 24
	.cfi_offset 6, -24
	pushq	%rbx
	.cfi_def_cfa_offset 32
	.cfi_offset 3, -32
	movq	%rsi, %rbp
	subq	$16, %rsp
	.cfi_def_cfa_offset 48
	movq	%rdi, %rbx
	movq	%rdx, %r12
	movq	%fs:40, %rax
	movq	%rax, 8(%rsp)
	xorl	%eax, %eax
	testq	%rdx, %rdx
	je	.L120
	testq	%rsi, %rsi
	je	.L137
.L120:
	subq	%rbp, %r12
	movq	%r12, (%rsp)
	cmpq	$15, %r12
	ja	.L138
	movq	(%rbx), %rdx
	movq	%rdx, %rdi
	cmpq	$1, %r12
	jne	.L123
	movzbl	0(%rbp), %eax
	movb	%al, (%rdx)
	movq	(%rbx), %rdx
.L124:
	movq	(%rsp), %rax
	movq	%rax, 8(%rbx)
	movb	$0, (%rdx,%rax)
	movq	8(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L139
	addq	$16, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 32
	popq	%rbx
	.cfi_def_cfa_offset 24
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	ret
.L123:
	.cfi_restore_state
	testq	%r12, %r12
	je	.L124
	jmp	.L122
.L138:
	movq	%rbx, %rdi
	movq	%rsp, %rsi
	xorl	%edx, %edx
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_createERmm@PLT
	movq	%rax, %rdi
	movq	%rax, (%rbx)
	movq	(%rsp), %rax
	movq	%rax, 16(%rbx)
.L122:
	movq	%r12, %rdx
	movq	%rbp, %rsi
	call	memcpy@PLT
	movq	(%rbx), %rdx
	jmp	.L124
.L137:
	leaq	.LC0(%rip), %rdi
	call	_ZSt19__throw_logic_errorPKc@PLT
.L139:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE7537:
	.size	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE12_M_constructIPcEEvT_S7_St20forward_iterator_tag.constprop.0, .-_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE12_M_constructIPcEEvT_S7_St20forward_iterator_tag.constprop.0
	.p2align 4
	.globl	_Z12localcomposeii
	.type	_Z12localcomposeii, @function
_Z12localcomposeii:
.LFB5627:
	.cfi_startproc
	endbr64
	movslq	%esi, %rax
	leaq	_ZL5words(%rip), %r9
	salq	$5, %rax
	addq	%r9, %rax
	movq	(%rax), %rdx
	movq	8(%rax), %r10
	addq	%rdx, %r10
	cmpq	%r10, %rdx
	je	.L141
	movq	%rdx, %rax
	movl	$1, %r8d
	jmp	.L144
	.p2align 4
	.p2align 3
.L142:
	cmpb	$83, %cl
	jne	.L143
	leal	(%r8,%r8), %ecx
	andl	$2, %ecx
	xorl	%ecx, %r8d
.L143:
	incq	%rax
	cmpq	%rax, %r10
	je	.L187
.L144:
	movzbl	(%rax), %ecx
	cmpb	$72, %cl
	jne	.L142
	leal	(%r8,%r8), %ecx
	incq	%rax
	sarl	%r8d
	andl	$2, %ecx
	orl	%ecx, %r8d
	cmpq	%rax, %r10
	jne	.L144
.L187:
	movslq	%edi, %rdi
	salq	$5, %rdi
	addq	%rdi, %r9
	movq	(%r9), %rax
	movq	8(%r9), %rdi
	addq	%rax, %rdi
	cmpq	%rax, %rdi
	je	.L169
.L171:
	movq	%rax, %rcx
	jmp	.L148
	.p2align 4
	.p2align 3
.L146:
	cmpb	$83, %sil
	jne	.L147
	leal	(%r8,%r8), %esi
	andl	$2, %esi
	xorl	%esi, %r8d
.L147:
	incq	%rcx
	cmpq	%rdi, %rcx
	je	.L188
.L148:
	movzbl	(%rcx), %esi
	cmpb	$72, %sil
	jne	.L146
	leal	(%r8,%r8), %esi
	incq	%rcx
	sarl	%r8d
	andl	$2, %esi
	orl	%esi, %r8d
	cmpq	%rdi, %rcx
	jne	.L148
.L188:
	movl	$2, %r9d
	cmpq	%r10, %rdx
	je	.L156
.L169:
	movl	$2, %r9d
	jmp	.L152
	.p2align 4
	.p2align 3
.L150:
	cmpb	$83, %cl
	jne	.L151
	leal	(%r9,%r9), %ecx
	andl	$2, %ecx
	xorl	%ecx, %r9d
.L151:
	incq	%rdx
	cmpq	%rdx, %r10
	je	.L185
.L152:
	movzbl	(%rdx), %ecx
	cmpb	$72, %cl
	jne	.L150
	leal	(%r9,%r9), %ecx
	sarl	%r9d
	andl	$2, %ecx
	orl	%ecx, %r9d
	jmp	.L151
	.p2align 4
	.p2align 3
.L154:
	cmpb	$83, %dl
	jne	.L155
	leal	(%r9,%r9), %edx
	andl	$2, %edx
	xorl	%edx, %r9d
.L155:
	incq	%rax
.L185:
	cmpq	%rax, %rdi
	je	.L153
.L156:
	movzbl	(%rax), %edx
	cmpb	$72, %dl
	jne	.L154
	leal	(%r9,%r9), %edx
	sarl	%r9d
	andl	$2, %edx
	orl	%edx, %r9d
	jmp	.L155
.L141:
	movslq	%edi, %rdi
	movl	$1, %r8d
	salq	$5, %rdi
	addq	%rdi, %r9
	movq	(%r9), %rax
	movq	8(%r9), %rdi
	movl	$2, %r9d
	addq	%rax, %rdi
	cmpq	%rax, %rdi
	jne	.L171
	.p2align 4
	.p2align 3
.L153:
	leaq	_ZL5words(%rip), %r11
	xorl	%r10d, %r10d
	.p2align 4
	.p2align 3
.L166:
	movq	(%r11), %rsi
	movq	8(%r11), %rdi
	addq	%rsi, %rdi
	cmpq	%rdi, %rsi
	je	.L157
	movq	%rsi, %rax
	movl	$1, %ecx
	jmp	.L160
	.p2align 4
	.p2align 3
.L158:
	cmpb	$83, %dl
	jne	.L159
	leal	(%rcx,%rcx), %edx
	andl	$2, %edx
	xorl	%edx, %ecx
.L159:
	leaq	1(%rax), %rdx
	cmpq	%rdx, %rdi
	je	.L189
.L172:
	movq	%rdx, %rax
.L160:
	movzbl	(%rax), %edx
	cmpb	$72, %dl
	jne	.L158
	leal	(%rcx,%rcx), %edx
	sarl	%ecx
	andl	$2, %edx
	orl	%edx, %ecx
	leaq	1(%rax), %rdx
	cmpq	%rdx, %rdi
	jne	.L172
.L189:
	cmpl	%ecx, %r8d
	je	.L190
.L167:
	incl	%r10d
	addq	$32, %r11
	cmpl	$6, %r10d
	jne	.L166
	xorl	%r10d, %r10d
	movl	%r10d, %eax
	ret
	.p2align 4
	.p2align 3
.L190:
	movl	$2, %ecx
	jmp	.L164
	.p2align 4
	.p2align 3
.L162:
	cmpb	$83, %dl
	jne	.L163
	leal	(%rcx,%rcx), %edx
	andl	$2, %edx
	xorl	%edx, %ecx
.L163:
	leaq	1(%rsi), %rdx
	cmpq	%rsi, %rax
	je	.L168
.L173:
	movq	%rdx, %rsi
.L164:
	movzbl	(%rsi), %edx
	cmpb	$72, %dl
	jne	.L162
	leal	(%rcx,%rcx), %edx
	sarl	%ecx
	andl	$2, %edx
	orl	%edx, %ecx
	leaq	1(%rsi), %rdx
	cmpq	%rsi, %rax
	jne	.L173
.L168:
	cmpl	%ecx, %r9d
	jne	.L167
.L186:
	movl	%r10d, %eax
	ret
	.p2align 4
	.p2align 3
.L157:
	cmpl	$1, %r8d
	jne	.L167
	movl	$2, %ecx
	cmpl	%ecx, %r9d
	jne	.L167
	jmp	.L186
	.cfi_endproc
.LFE5627:
	.size	_Z12localcomposeii, .-_Z12localcomposeii
	.p2align 4
	.globl	_Z7countcxRK7Circuit
	.type	_Z7countcxRK7Circuit, @function
_Z7countcxRK7Circuit:
.LFB5645:
	.cfi_startproc
	endbr64
	movq	(%rdi), %rdx
	movq	8(%rdi), %rcx
	xorl	%r8d, %r8d
	cmpq	%rdx, %rcx
	je	.L191
	.p2align 4
	.p2align 3
.L193:
	movq	88(%rdx), %rax
	subq	80(%rdx), %rax
	addq	$104, %rdx
	sarq	$3, %rax
	addl	%eax, %r8d
	cmpq	%rdx, %rcx
	jne	.L193
.L191:
	movl	%r8d, %eax
	ret
	.cfi_endproc
.LFE5645:
	.size	_Z7countcxRK7Circuit, .-_Z7countcxRK7Circuit
	.p2align 4
	.globl	_Z7maprowsRK7CircuitPmSt5arrayIiLm3EE
	.type	_Z7maprowsRK7CircuitPmSt5arrayIiLm3EE, @function
_Z7maprowsRK7CircuitPmSt5arrayIiLm3EE:
.LFB5693:
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
	movq	%rsi, %r8
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movl	nq(%rip), %ebp
	movl	%ecx, -8(%rsp)
	movq	%rdx, -16(%rsp)
	leal	(%rbp,%rbp), %ecx
	testl	%ecx, %ecx
	jle	.L197
	movslq	%ecx, %rcx
	xorl	%eax, %eax
	movl	$1, %esi
	.p2align 4
	.p2align 3
.L198:
	shlx	%rax, %rsi, %rdx
	movq	%rdx, (%r8,%rax,8)
	incq	%rax
	cmpq	%rax, %rcx
	jne	.L198
.L197:
	movq	8(%rdi), %rax
	movq	(%rdi), %r10
	movq	%rax, -32(%rsp)
	cmpq	%r10, %rax
	je	.L219
	movl	-8(%rsp), %eax
	vpxor	%xmm0, %xmm0, %xmm0
	leaq	.L203(%rip), %r15
	movl	%ebp, %r13d
	movl	-16(%rsp), %r9d
	movl	-12(%rsp), %r11d
	movl	%eax, -36(%rsp)
	movslq	%ebp, %rax
	leaq	(%r8,%rax,8), %rax
	movq	%rax, -24(%rsp)
	leal	-1(%rbp), %eax
	leaq	8(%r8,%rax,8), %rdi
	.p2align 4
	.p2align 3
.L200:
	movq	-24(%rsp), %rsi
	movq	%r10, %rdx
	movq	%r8, %rax
	testl	%r13d, %r13d
	jle	.L212
	.p2align 4
	.p2align 3
.L208:
	cmpl	$5, (%rdx)
	movq	(%rax), %rbx
	movq	(%rsi), %rbp
	ja	.L201
	movl	(%rdx), %ecx
	movslq	(%r15,%rcx,4), %rcx
	addq	%r15, %rcx
	notrack jmp	*%rcx
	.section	.rodata
	.align 4
	.align 4
.L203:
	.long	.L201-.L203
	.long	.L221-.L203
	.long	.L222-.L203
	.long	.L205-.L203
	.long	.L204-.L203
	.long	.L202-.L203
	.text
	.p2align 4
	.p2align 3
.L205:
	movq	%rbp, (%rax)
.L222:
	xorq	%rbp, %rbx
	movq	%rbx, (%rsi)
.L201:
	addq	$8, %rax
	addq	$8, %rsi
	addq	$4, %rdx
	cmpq	%rax, %rdi
	jne	.L208
.L212:
	movq	80(%r10), %rbx
	movq	88(%r10), %rsi
	cmpq	%rsi, %rbx
	je	.L209
	movq	%rbx, %rdx
	vmovd	%xmm0, %eax
	.p2align 4
	.p2align 3
.L211:
	cmpl	%eax, %r9d
	je	.L210
	cmpl	%eax, %r11d
	je	.L210
	cmpl	%eax, -36(%rsp)
	je	.L210
	movslq	(%rdx), %r12
	movslq	4(%rdx), %r14
	movq	%r12, %rcx
	movq	%r14, %rbp
	movq	(%r8,%r12,8), %r12
	xorq	%r12, (%r8,%r14,8)
	addl	%r13d, %ecx
	addl	%r13d, %ebp
	movslq	%ecx, %rcx
	movslq	%ebp, %rbp
	movq	(%r8,%rbp,8), %rbp
	xorq	%rbp, (%r8,%rcx,8)
.L210:
	addq	$8, %rdx
	incl	%eax
	cmpq	%rdx, %rsi
	jne	.L211
	subq	$8, %rsi
	vmovd	%xmm0, %eax
	subq	%rbx, %rsi
	shrq	$3, %rsi
	leal	1(%rax,%rsi), %eax
	vmovd	%eax, %xmm0
.L209:
	addq	$104, %r10
	cmpq	%r10, -32(%rsp)
	jne	.L200
.L219:
	popq	%rbx
	.cfi_remember_state
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
.L204:
	.cfi_restore_state
	xorq	%rbx, %rbp
.L221:
	movq	%rbp, (%rax)
	movq	%rbx, (%rsi)
	jmp	.L201
	.p2align 4
	.p2align 3
.L202:
	xorq	%rbp, %rbx
	movq	%rbx, (%rax)
	jmp	.L201
	.cfi_endproc
.LFE5693:
	.size	_Z7maprowsRK7CircuitPmSt5arrayIiLm3EE, .-_Z7maprowsRK7CircuitPmSt5arrayIiLm3EE
	.p2align 4
	.globl	_Z14imagesfromrowsPKmPmS1_
	.type	_Z14imagesfromrowsPKmPmS1_, @function
_Z14imagesfromrowsPKmPmS1_:
.LFB5696:
	.cfi_startproc
	endbr64
	movl	nq(%rip), %r8d
	leal	(%r8,%r8), %r10d
	testl	%r10d, %r10d
	jle	.L237
	movq	$-1, %r11
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset 3, -16
	movslq	%r10d, %r9
	movq	%rdx, %rbx
	shlx	%r8, %r11, %r11
	xorl	%ecx, %ecx
	notq	%r11
	.p2align 4
	.p2align 3
.L225:
	leal	(%r8,%rcx), %eax
	movq	$0, (%rsi,%rcx,8)
	cltd
	idivl	%r10d
	movq	%r11, %rax
	movslq	%edx, %rdx
	movq	(%rdi,%rdx,8), %rdx
	andq	%rdx, %rax
	shrx	%r8, %rdx, %rdx
	shlx	%r8, %rax, %rax
	orq	%rdx, %rax
	movq	%rax, (%rbx,%rcx,8)
	incq	%rcx
	cmpq	%rcx, %r9
	jne	.L225
	xorl	%r8d, %r8d
	movl	$1, %r10d
	.p2align 4
	.p2align 3
.L228:
	movq	(%rdi,%r8,8), %rax
	testq	%rax, %rax
	je	.L226
	shlx	%r8, %r10, %rcx
	.p2align 4
	.p2align 3
.L227:
	tzcntq	%rax, %rdx
	orq	%rcx, (%rsi,%rdx,8)
	blsr	%rax, %rax
	jne	.L227
.L226:
	incq	%r8
	cmpq	%r8, %r9
	jne	.L228
	popq	%rbx
	.cfi_def_cfa_offset 8
	ret
.L237:
	.cfi_restore 3
	ret
	.cfi_endproc
.LFE5696:
	.size	_Z14imagesfromrowsPKmPmS1_, .-_Z14imagesfromrowsPKmPmS1_
	.p2align 4
	.globl	_Z8evaluateRK7Circuit
	.type	_Z8evaluateRK7Circuit, @function
_Z8evaluateRK7Circuit:
.LFB5698:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	vmovq	%rdi, %xmm8
	movl	$1, %ecx
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	andq	$-64, %rsp
	subq	$1536, %rsp
	.cfi_offset 15, -24
	.cfi_offset 14, -32
	.cfi_offset 13, -40
	.cfi_offset 12, -48
	.cfi_offset 3, -56
	movl	nq(%rip), %ebx
	movq	%fs:40, %rax
	movq	%rax, 1528(%rsp)
	xorl	%eax, %eax
	leaq	64(%rsp), %rdi
	leal	(%rbx,%rbx), %edx
	movslq	%edx, %r8
	testl	%edx, %edx
	jle	.L245
	.p2align 4
	.p2align 3
.L244:
	shlx	%rax, %rcx, %rdx
	movq	%rdx, (%rdi,%rax,8)
	incq	%rax
	cmpq	%rax, %r8
	jne	.L244
.L245:
	movq	(%rsi), %r9
	movq	8(%rsi), %r10
	movslq	%ebx, %rax
	vmovq	%rax, %xmm14
	cmpq	%r10, %r9
	je	.L308
	leaq	(%rdi,%rax,8), %r11
	leal	-1(%rbx), %eax
	leaq	.L248(%rip), %r15
	movl	%eax, 48(%rsp)
	leaq	72(%rsp,%rax,8), %r8
	.p2align 4
	.p2align 3
.L255:
	movq	%r9, %rdx
	movq	%r11, %rsi
	movq	%rdi, %rax
	testl	%ebx, %ebx
	jle	.L258
	.p2align 4
	.p2align 3
.L253:
	cmpl	$5, (%rdx)
	movq	(%rax), %r12
	movq	(%rsi), %r13
	ja	.L246
	movl	(%rdx), %ecx
	movslq	(%r15,%rcx,4), %rcx
	addq	%r15, %rcx
	notrack jmp	*%rcx
	.section	.rodata
	.align 4
	.align 4
.L248:
	.long	.L246-.L248
	.long	.L306-.L248
	.long	.L307-.L248
	.long	.L250-.L248
	.long	.L249-.L248
	.long	.L247-.L248
	.text
	.p2align 4
	.p2align 3
.L250:
	movq	%r13, (%rax)
.L307:
	xorq	%r13, %r12
	movq	%r12, (%rsi)
.L246:
	addq	$8, %rax
	addq	$8, %rsi
	addq	$4, %rdx
	cmpq	%rax, %r8
	jne	.L253
.L258:
	movq	88(%r9), %rsi
	movq	80(%r9), %rcx
	cmpq	%rsi, %rcx
	je	.L257
	.p2align 4
	.p2align 3
.L256:
	movslq	(%rcx), %r13
	movslq	4(%rcx), %r12
	addq	$8, %rcx
	movq	%r13, %rax
	movq	%r12, %rdx
	movq	64(%rsp,%r13,8), %r13
	xorq	%r13, (%rdi,%r12,8)
	addl	%ebx, %eax
	addl	%ebx, %edx
	cltq
	movslq	%edx, %rdx
	movq	64(%rsp,%rdx,8), %rdx
	xorq	%rdx, (%rdi,%rax,8)
	cmpq	%rcx, %rsi
	jne	.L256
.L257:
	addq	$104, %r9
	cmpq	%r9, %r10
	jne	.L255
.L243:
	leaq	704(%rsp), %rax
	leaq	384(%rsp), %r9
	vxorps	%xmm5, %xmm5, %xmm5
	movq	$-1, %r13
	movq	%rax, %rdx
	movq	%r9, %rsi
	movq	%rax, 24(%rsp)
	movq	%r9, 56(%rsp)
	call	_Z14imagesfromrowsPKmPmS1_
	vmovq	%xmm8, %rax
	shlx	%rbx, %r13, %r13
	vxorpd	%xmm12, %xmm12, %xmm12
	vmovapd	.LC3(%rip), %xmm0
	vmovsd	targetmean(%rip), %xmm16
	notq	%r13
	leal	(%rbx,%rbx,2), %ecx
	vmovsd	8+targetmean(%rip), %xmm15
	vmovsd	.LC1(%rip), %xmm10
	vmovq	%xmm8, 40(%rsp)
	vmovsd	%xmm12, %xmm12, %xmm2
	vmovdqa64	.LC10(%rip), %ymm24
	movq	%r13, %r14
	vcvtsi2sdl	%ecx, %xmm5, %xmm20
	vmovdqa64	.LC11(%rip), %ymm23
	vmovdqa64	.LC12(%rip), %ymm22
	vmovdqa64	.LC13(%rip), %ymm21
	vmovdqa64	.LC4(%rip), %zmm30
	vmovdqa64	.LC5(%rip), %zmm29
	vmovdqa64	.LC6(%rip), %zmm28
	vmovdqa64	.LC7(%rip), %zmm27
	vmovdqa64	.LC8(%rip), %zmm26
	vmovdqa64	.LC9(%rip), %zmm25
	movl	4+targetmin(%rip), %esi
	vmovupd	%xmm0, 48(%rax)
	movl	targetmin(%rip), %eax
	movq	56(%rsp), %r9
	vcvtsi2sdl	%esi, %xmm5, %xmm17
	movl	%eax, 52(%rsp)
	vcvtsi2sdl	%eax, %xmm5, %xmm19
	movl	48(%rsp), %eax
	imull	%ebx, %eax
	leal	(%rax,%rax,8), %edx
	movl	%edx, %eax
	shrl	$31, %eax
	addl	%edx, %eax
	sarl	%eax
	vcvtsi2sdl	%eax, %xmm5, %xmm18
	vmovq	%xmm8, %rax
	addq	$24, %rax
	vmovq	%rax, %xmm7
	vmovq	%xmm8, %rax
	addq	$16, %rax
	vmovdqa	%xmm7, %xmm9
	movq	%rax, 32(%rsp)
	movl	%ebx, %eax
	shrl	$3, %eax
	movl	%eax, 16(%rsp)
	vmovq	%xmm14, %rax
	salq	$3, %rax
	vmovq	%rax, %xmm31
	movl	%ebx, %eax
	andl	$-8, %eax
	vmovdqa64	%xmm31, %xmm7
	movl	%eax, 20(%rsp)
.L279:
	testl	%ebx, %ebx
	jle	.L264
	cmpl	$6, 48(%rsp)
	jbe	.L282
	vmovq	%xmm7, %rax
	vmovdqu64	(%r9), %zmm6
	addq	%r9, %rax
	cmpl	$1, 16(%rsp)
	vpxorq	(%rax), %zmm6, %zmm0
	vmovdqa64	%zmm6, %zmm1
	vmovdqa64	%zmm6, %zmm3
	vpermt2q	%zmm0, %zmm30, %zmm1
	vpermt2q	%zmm0, %zmm28, %zmm3
	vpermt2q	%zmm6, %zmm26, %zmm0
	vpermt2q	(%rax), %zmm29, %zmm1
	vpermt2q	(%rax), %zmm25, %zmm0
	vmovdqa64	%zmm1, 1024(%rsp)
	vmovdqu64	(%rax), %zmm1
	vmovdqa64	%zmm0, 1152(%rsp)
	vpermt2q	%zmm3, %zmm27, %zmm1
	vmovdqa64	%zmm1, 1088(%rsp)
	jbe	.L263
	vmovdqu64	64(%rax), %zmm1
	vpxorq	64(%r9), %zmm1, %zmm0
	vmovdqu64	64(%r9), %zmm3
	vmovdqu64	64(%r9), %zmm4
	vpermt2q	%zmm0, %zmm30, %zmm3
	vpermt2q	%zmm1, %zmm29, %zmm3
	vpermt2q	%zmm0, %zmm28, %zmm4
	vpermt2q	64(%r9), %zmm26, %zmm0
	vmovdqa64	%zmm3, 1216(%rsp)
	vmovdqa64	%zmm1, %zmm3
	vpermt2q	%zmm1, %zmm25, %zmm0
	vpermt2q	%zmm4, %zmm27, %zmm3
	vmovdqa64	%zmm0, 1344(%rsp)
	vmovdqa64	%zmm3, 1280(%rsp)
.L263:
	movl	20(%rsp), %eax
	movl	%eax, %edi
	cmpl	%ebx, %eax
	je	.L264
.L262:
	movl	%ebx, %edx
	leaq	1024(%rsp), %r10
	subl	%edi, %edx
	leal	-1(%rdx), %r8d
	cmpl	$2, %r8d
	jbe	.L266
	vmovq	%xmm14, %r11
	vmovdqu	(%r9,%rdi,8), %ymm0
	leaq	(%rdi,%rdi,2), %r8
	addq	%r11, %rdi
	leaq	1024(%rsp,%r8,8), %r8
	vmovdqu	(%r9,%rdi,8), %ymm1
	movl	%edx, %edi
	andl	$-4, %edi
	addl	%edi, %eax
	vmovdqa	%ymm0, %ymm4
	vpxor	%ymm0, %ymm1, %ymm3
	vpermt2q	%ymm3, %ymm24, %ymm4
	vpermt2q	%ymm1, %ymm23, %ymm4
	vmovdqa	%ymm4, (%r8)
	vmovdqa	%ymm3, %ymm4
	vpermt2q	%ymm0, %ymm22, %ymm4
	vpermt2q	%ymm3, %ymm21, %ymm0
	vmovdqa	.LC14(%rip), %ymm3
	vpblendd	$12, %ymm1, %ymm4, %ymm4
	vmovdqa	%ymm4, 32(%r8)
	vpermt2q	%ymm0, %ymm3, %ymm1
	vmovdqa	%ymm1, 64(%r8)
	cmpl	%edx, %edi
	je	.L264
.L266:
	movslq	%eax, %r8
	leal	(%rbx,%rax), %edi
	leal	(%rax,%rax,2), %edx
	salq	$3, %r8
	movslq	%edi, %rdi
	vmovq	(%r9,%r8), %xmm6
	movq	(%r9,%rdi,8), %r13
	movq	(%r9,%r8), %rdi
	xorq	%r13, %rdi
	vpinsrq	$1, %rdi, %xmm6, %xmm0
	movslq	%edx, %rdi
	vmovdqu	%xmm0, (%r10,%rdi,8)
	leal	2(%rdx), %edi
	movslq	%edi, %rdi
	movq	%r13, 1024(%rsp,%rdi,8)
	leal	1(%rax), %edi
	cmpl	%edi, %ebx
	jle	.L264
	vmovq	8(%r9,%r8), %xmm6
	addl	%ebx, %edi
	addl	$2, %eax
	movslq	%edi, %rdi
	movq	(%r9,%rdi,8), %r13
	movq	8(%r9,%r8), %rdi
	xorq	%r13, %rdi
	vpinsrq	$1, %rdi, %xmm6, %xmm0
	leal	3(%rdx), %edi
	movslq	%edi, %rdi
	vmovdqu	%xmm0, (%r10,%rdi,8)
	leal	5(%rdx), %edi
	movslq	%edi, %rdi
	movq	%r13, 1024(%rsp,%rdi,8)
	cmpl	%eax, %ebx
	jle	.L264
	addl	%ebx, %eax
	movq	16(%r9,%r8), %r8
	cltq
	movq	(%r9,%rax,8), %rdi
	vmovq	%r8, %xmm6
	movq	%rdi, %rax
	xorq	%r8, %rax
	vpinsrq	$1, %rax, %xmm6, %xmm0
	leal	6(%rdx), %eax
	addl	$8, %edx
	cltq
	movslq	%edx, %rdx
	vmovdqu	%xmm0, (%r10,%rax,8)
	movq	%rdi, 1024(%rsp,%rdx,8)
.L264:
	testl	%ecx, %ecx
	jle	.L309
	leaq	1024(%rsp), %r10
	movslq	%ecx, %rax
	xorl	%r12d, %r12d
	movl	%ebx, %r13d
	movq	%r10, %r15
	movq	%rax, 56(%rsp)
	xorl	%edi, %edi
	xorl	%r11d, %r11d
	movl	%ebx, %r9d
	movl	%r12d, %r10d
	.p2align 4
	.p2align 3
.L270:
	movq	(%r15,%rdi,8), %r12
	movl	52(%rsp), %eax
	shrx	%rbx, %r12, %rdx
	orq	%r12, %rdx
	andq	%r14, %rdx
	popcntq	%rdx, %rdx
	addl	%edx, %r10d
	cmpl	%edx, %r9d
	cmovg	%edx, %r9d
	subl	%edx, %eax
	movl	$0, %edx
	cmovs	%edx, %eax
	movl	$2863311531, %edx
	imull	%eax, %eax
	addl	%eax, %eax
	vcvtsi2sdl	%eax, %xmm5, %xmm0
	movl	%edi, %eax
	vaddsd	%xmm0, %xmm2, %xmm2
	imulq	%rdx, %rax
	shrq	$33, %rax
	leal	1(%rax), %edx
	leal	3(%rax,%rax,2), %r8d
	cmpl	%ebx, %edx
	jge	.L268
	movslq	%r8d, %r8
	.p2align 4
	.p2align 3
.L269:
	movq	(%r15,%r8,8), %rdx
	xorq	%r12, %rdx
	shrx	%rbx, %rdx, %rax
	orq	%rdx, %rax
	movl	%esi, %edx
	andq	%r14, %rax
	popcntq	%rax, %rax
	addl	%eax, %r11d
	cmpl	%eax, %r13d
	cmovg	%eax, %r13d
	subl	%eax, %edx
	movl	$0, %eax
	cmovs	%eax, %edx
	incq	%r8
	imull	%edx, %edx
	vcvtsi2sdl	%edx, %xmm5, %xmm0
	vaddsd	%xmm0, %xmm2, %xmm2
	cmpl	%r8d, %ecx
	jg	.L269
.L268:
	incq	%rdi
	cmpq	%rdi, 56(%rsp)
	jne	.L270
	movl	%r9d, %r15d
	vcvtsi2sdl	%r10d, %xmm5, %xmm0
	vcvtsi2sdl	%r11d, %xmm5, %xmm3
.L261:
	vdivsd	%xmm20, %xmm0, %xmm0
	vmovsd	%xmm12, %xmm12, %xmm1
	vsubsd	%xmm0, %xmm16, %xmm6
	vcomisd	%xmm12, %xmm6
	jbe	.L271
	vmulsd	.LC15(%rip), %xmm6, %xmm1
	vmulsd	%xmm6, %xmm1, %xmm1
.L271:
	movq	40(%rsp), %rax
	vdivsd	%xmm18, %xmm3, %xmm3
	vcvtsi2sdl	%r15d, %xmm5, %xmm4
	vaddsd	%xmm1, %xmm2, %xmm1
	vmovsd	%xmm12, %xmm12, %xmm2
	movl	%r15d, (%rax)
	vmovq	%xmm9, %rax
	vmovsd	%xmm0, -8(%rax)
	vdivsd	%xmm19, %xmm4, %xmm4
	vdivsd	%xmm16, %xmm0, %xmm0
	vminsd	%xmm4, %xmm0, %xmm0
	vsubsd	%xmm3, %xmm15, %xmm4
	vminsd	%xmm10, %xmm0, %xmm0
	vcomisd	%xmm12, %xmm4
	jbe	.L275
	vmulsd	.LC15(%rip), %xmm4, %xmm2
	vmulsd	%xmm4, %xmm2, %xmm2
.L275:
	vaddsd	%xmm2, %xmm1, %xmm2
	vdivsd	%xmm15, %xmm3, %xmm10
	vcvtsi2sdl	%r13d, %xmm5, %xmm1
	vmovq	%xmm8, %rax
	vmovq	%xmm9, %rdi
	movq	24(%rsp), %r9
	vmovsd	%xmm2, 48(%rax)
	movq	40(%rsp), %rax
	movl	%r13d, 4(%rax)
	vmovsd	%xmm3, (%rdi)
	vmovq	%xmm8, %rdi
	addq	$8, %rax
	movq	%rax, 40(%rsp)
	vdivsd	%xmm17, %xmm1, %xmm1
	vminsd	%xmm1, %xmm10, %xmm10
	vminsd	%xmm0, %xmm10, %xmm10
	vmovsd	%xmm10, 56(%rdi)
	vmovq	%xmm9, %rdi
	addq	$16, %rdi
	vmovq	%rdi, %xmm9
	cmpq	32(%rsp), %rax
	jne	.L279
	movq	1528(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L310
	vmovq	%xmm8, %rax
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
	.p2align 4
	.p2align 3
.L249:
	.cfi_restore_state
	xorq	%r12, %r13
.L306:
	movq	%r13, (%rax)
	movq	%r12, (%rsi)
	jmp	.L246
	.p2align 4
	.p2align 3
.L247:
	xorq	%r13, %r12
	movq	%r12, (%rax)
	jmp	.L246
.L309:
	movl	%ebx, %r13d
	movl	%ebx, %r15d
	vmovsd	%xmm12, %xmm12, %xmm3
	vmovsd	%xmm12, %xmm12, %xmm0
	jmp	.L261
.L282:
	xorl	%edi, %edi
	xorl	%eax, %eax
	jmp	.L262
.L308:
	leal	-1(%rbx), %eax
	movl	%eax, 48(%rsp)
	jmp	.L243
.L310:
	vzeroupper
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE5698:
	.size	_Z8evaluateRK7Circuit, .-_Z8evaluateRK7Circuit
	.section	.rodata.str1.1,"aMS",@progbits,1
.LC16:
	.string	" E="
.LC17:
	.string	" ratio="
.LC18:
	.string	" min="
.LC19:
	.string	" mean="
	.text
	.p2align 4
	.globl	_Z12printmetricsRK7Metrics
	.type	_Z12printmetricsRK7Metrics, @function
_Z12printmetricsRK7Metrics:
.LFB5711:
	.cfi_startproc
	endbr64
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	pushq	%r13
	.cfi_def_cfa_offset 24
	.cfi_offset 13, -24
	pushq	%r12
	.cfi_def_cfa_offset 32
	.cfi_offset 12, -32
	leaq	_ZSt4cerr(%rip), %r12
	pushq	%rbp
	.cfi_def_cfa_offset 40
	.cfi_offset 6, -40
	pushq	%rbx
	.cfi_def_cfa_offset 48
	.cfi_offset 3, -48
	movq	%rdi, %r14
	movl	$3, %edx
	subq	$16, %rsp
	.cfi_def_cfa_offset 64
	leaq	.LC16(%rip), %rsi
	movq	%r12, %rdi
	leaq	16(%r14), %rbx
	movq	%fs:40, %rax
	movq	%rax, 8(%rsp)
	xorl	%eax, %eax
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	vmovsd	48(%r14), %xmm0
	movq	%r12, %rdi
	leaq	7(%rsp), %r13
	call	_ZNSo9_M_insertIdEERSoT_@PLT
	movl	$7, %edx
	leaq	.LC17(%rip), %rsi
	movq	%rax, %rdi
	movq	%rax, %rbp
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	vmovsd	56(%r14), %xmm0
	movq	%rbp, %rdi
	movq	%r14, %rbp
	call	_ZNSo9_M_insertIdEERSoT_@PLT
	movl	$5, %edx
	leaq	.LC18(%rip), %rsi
	movq	%rax, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
.L312:
	movl	0(%rbp), %esi
	movq	%r12, %rdi
	addq	$4, %rbp
	call	_ZNSolsEi@PLT
	movl	$1, %edx
	movq	%r13, %rsi
	movb	$44, 7(%rsp)
	movq	%rax, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	cmpq	%rbp, %rbx
	jne	.L312
	movl	$6, %edx
	leaq	.LC19(%rip), %rsi
	movq	%r12, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	addq	$48, %r14
.L313:
	vmovsd	(%rbx), %xmm0
	movq	%r12, %rdi
	addq	$8, %rbx
	call	_ZNSo9_M_insertIdEERSoT_@PLT
	movl	$1, %edx
	movq	%r13, %rsi
	movb	$44, 7(%rsp)
	movq	%rax, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	cmpq	%rbx, %r14
	jne	.L313
	movq	8(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L319
	addq	$16, %rsp
	.cfi_remember_state
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
.L319:
	.cfi_restore_state
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE5711:
	.size	_Z12printmetricsRK7Metrics, .-_Z12printmetricsRK7Metrics
	.p2align 4
	.globl	_Z14singlecriticalPKm
	.type	_Z14singlecriticalPKm, @function
_Z14singlecriticalPKm:
.LFB5789:
	.cfi_startproc
	endbr64
	movl	nq(%rip), %r10d
	testl	%r10d, %r10d
	jle	.L323
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	leal	-1(%r10), %eax
	movq	$-1, %r15
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	leaq	8(%rdi,%rax,8), %rax
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	shlx	%r10, %r15, %r15
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	vpxor	%xmm3, %xmm3, %xmm3
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	movslq	%r10d, %rsi
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rax, -8(%rsp)
	notq	%r15
	vpxor	%xmm0, %xmm0, %xmm0
	xorl	%r11d, %r11d
	xorl	%r8d, %r8d
	xorl	%ebx, %ebx
	xorl	%r9d, %r9d
	xorl	%eax, %eax
	vmovq	%rsi, %xmm4
	vmovdqa	%xmm3, %xmm1
	.p2align 4
	.p2align 3
.L322:
	movq	(%rdi), %rdx
	vmovq	%xmm4, %rsi
	movl	$3, %ecx
	movq	(%rdi,%rsi,8), %rbp
	movq	%rdx, %r13
	shrx	%r10, %rdx, %rsi
	movq	%rdx, %r12
	orq	%rsi, %r13
	xorq	%rbp, %r12
	shrx	%r10, %rbp, %r14
	andq	%r15, %r13
	popcntq	%r13, %r13
	subl	%r13d, %ecx
	movl	$0, %r13d
	cmovs	%r13d, %ecx
	movq	%rbp, %r13
	imull	%ecx, %ecx
	orq	%r14, %r13
	andq	%r15, %r13
	popcntq	%r13, %r13
	addl	%eax, %ecx
	movl	$3, %eax
	subl	%r13d, %eax
	movl	$0, %r13d
	cmovs	%r13d, %eax
	imull	%eax, %eax
	addl	%ecx, %eax
	shrx	%r10, %r12, %rcx
	orq	%rcx, %r12
	movl	$3, %ecx
	andq	%r15, %r12
	popcntq	%r12, %r12
	subl	%r12d, %ecx
	movl	$0, %r12d
	cmovs	%r12d, %ecx
	addq	$8, %rdi
	imull	%ecx, %ecx
	addl	%ecx, %eax
	movq	%rdx, %rcx
	xorq	%rsi, %rdx
	vmovq	%xmm1, %rsi
	orq	%rbp, %rcx
	xorq	%r14, %rbp
	orq	%rbp, %rdx
	movq	%rcx, %rbp
	andq	%rbx, %rbp
	andq	%r15, %rdx
	orq	%rbp, %rsi
	movq	%r9, %rbp
	orq	%rcx, %r9
	andq	%rcx, %rbp
	movq	%rdx, %rcx
	vmovq	%rsi, %xmm1
	vmovq	%xmm0, %rsi
	andq	%r11, %rcx
	orq	%rbp, %rbx
	orq	%rcx, %rsi
	movq	%r8, %rcx
	orq	%rdx, %r8
	andq	%rdx, %rcx
	vmovq	%rsi, %xmm0
	orq	%rcx, %r11
	cmpq	%rdi, -8(%rsp)
	jne	.L322
	vmovq	%xmm1, %rdi
	andn	%r9, %rbx, %r9
	andn	%r8, %r11, %r8
	andn	%r11, %rsi, %rdx
	andn	%rbx, %rdi, %rcx
	popcntq	%r9, %r9
	popcntq	%r8, %r8
	popcntq	%rdx, %rdx
	popcntq	%rcx, %rcx
	leal	(%rdx,%r8,4), %edx
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	leal	(%rcx,%r9,4), %ecx
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	addl	%ecx, %eax
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	addl	%edx, %eax
	ret
.L323:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	xorl	%eax, %eax
	ret
	.cfi_endproc
.LFE5789:
	.size	_Z14singlecriticalPKm, .-_Z14singlecriticalPKm
	.section	.rodata._ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_.str1.1,"aMS",@progbits,1
.LC20:
	.string	"basic_string::append"
	.section	.text._ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_,"axG",@progbits,_ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_,comdat
	.p2align 4
	.weak	_ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_
	.type	_ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_, @function
_ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_:
.LFB6121:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA6121
	endbr64
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	pushq	%r13
	.cfi_def_cfa_offset 24
	.cfi_offset 13, -24
	pushq	%r12
	.cfi_def_cfa_offset 32
	.cfi_offset 12, -32
	movq	%rdi, %r12
	pushq	%rbp
	.cfi_def_cfa_offset 40
	.cfi_offset 6, -40
	pushq	%rbx
	.cfi_def_cfa_offset 48
	.cfi_offset 3, -48
	leaq	16(%rdi), %rbx
	movq	%rdx, %rbp
	subq	$16, %rsp
	.cfi_def_cfa_offset 64
	movq	8(%rsi), %r13
	movq	%fs:40, %rax
	movq	%rax, 8(%rsp)
	xorl	%eax, %eax
	movq	%rbx, (%rdi)
	movq	(%rsi), %r14
	movq	%r14, %rax
	addq	%r13, %rax
	je	.L330
	testq	%r14, %r14
	je	.L350
.L330:
	movq	%r13, (%rsp)
	cmpq	$15, %r13
	ja	.L351
	cmpq	$1, %r13
	jne	.L333
	movzbl	(%r14), %eax
	movb	%al, 16(%r12)
	movq	%rbx, %rax
.L334:
	movq	%r13, 8(%r12)
	movq	%rbp, %rdi
	movb	$0, (%rax,%r13)
	call	strlen@PLT
	movq	%rax, %rdx
	movabsq	$4611686018427387903, %rax
	subq	8(%r12), %rax
	cmpq	%rax, %rdx
	ja	.L352
	movq	%rbp, %rsi
	movq	%r12, %rdi
.LEHB0:
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_appendEPKcm@PLT
.LEHE0:
	movq	8(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L353
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
.L333:
	.cfi_restore_state
	testq	%r13, %r13
	jne	.L354
	movq	%rbx, %rax
	jmp	.L334
	.p2align 4
	.p2align 3
.L351:
	movq	%r12, %rdi
	movq	%rsp, %rsi
	xorl	%edx, %edx
.LEHB1:
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_createERmm@PLT
	movq	%rax, %rdi
	movq	%rax, (%r12)
	movq	(%rsp), %rax
	movq	%rax, 16(%r12)
.L332:
	movq	%r13, %rdx
	movq	%r14, %rsi
	call	memcpy@PLT
	movq	(%rsp), %r13
	movq	(%r12), %rax
	jmp	.L334
.L350:
	leaq	.LC0(%rip), %rdi
	call	_ZSt19__throw_logic_errorPKc@PLT
.LEHE1:
.L352:
	leaq	.LC20(%rip), %rdi
.LEHB2:
	call	_ZSt20__throw_length_errorPKc@PLT
.LEHE2:
.L353:
	call	__stack_chk_fail@PLT
.L354:
	movq	%rbx, %rdi
	jmp	.L332
.L340:
	endbr64
	movq	%rax, %rbp
.L336:
	movq	(%r12), %rdi
	cmpq	%rdi, %rbx
	je	.L348
	movq	16(%r12), %rsi
	incq	%rsi
	vzeroupper
	call	_ZdlPvm@PLT
.L337:
	movq	%rbp, %rdi
.LEHB3:
	call	_Unwind_Resume@PLT
.LEHE3:
.L348:
	vzeroupper
	jmp	.L337
	.cfi_endproc
.LFE6121:
	.globl	__gxx_personality_v0
	.section	.gcc_except_table._ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_,"aG",@progbits,_ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_,comdat
.LLSDA6121:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE6121-.LLSDACSB6121
.LLSDACSB6121:
	.uleb128 .LEHB0-.LFB6121
	.uleb128 .LEHE0-.LEHB0
	.uleb128 .L340-.LFB6121
	.uleb128 0
	.uleb128 .LEHB1-.LFB6121
	.uleb128 .LEHE1-.LEHB1
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB2-.LFB6121
	.uleb128 .LEHE2-.LEHB2
	.uleb128 .L340-.LFB6121
	.uleb128 0
	.uleb128 .LEHB3-.LFB6121
	.uleb128 .LEHE3-.LEHB3
	.uleb128 0
	.uleb128 0
.LLSDACSE6121:
	.section	.text._ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_,"axG",@progbits,_ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_,comdat
	.size	_ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_, .-_ZStplIcSt11char_traitsIcESaIcEENSt7__cxx1112basic_stringIT_T0_T1_EERKS8_PKS5_
	.section	.text._ZNSt6vectorI5LayerSaIS0_EED2Ev,"axG",@progbits,_ZNSt6vectorI5LayerSaIS0_EED5Ev,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI5LayerSaIS0_EED2Ev
	.type	_ZNSt6vectorI5LayerSaIS0_EED2Ev, @function
_ZNSt6vectorI5LayerSaIS0_EED2Ev:
.LFB6277:
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
	je	.L356
	.p2align 4
	.p2align 3
.L360:
	movq	80(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L357
	movq	96(%rbp), %rsi
	addq	$104, %rbp
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	cmpq	%rbp, %rbx
	jne	.L360
.L359:
	movq	(%r12), %rbp
.L356:
	testq	%rbp, %rbp
	je	.L362
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
.L357:
	.cfi_restore_state
	addq	$104, %rbp
	cmpq	%rbp, %rbx
	jne	.L360
	jmp	.L359
	.p2align 4
	.p2align 3
.L362:
	popq	%rbx
	.cfi_def_cfa_offset 24
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE6277:
	.size	_ZNSt6vectorI5LayerSaIS0_EED2Ev, .-_ZNSt6vectorI5LayerSaIS0_EED2Ev
	.weak	_ZNSt6vectorI5LayerSaIS0_EED1Ev
	.set	_ZNSt6vectorI5LayerSaIS0_EED1Ev,_ZNSt6vectorI5LayerSaIS0_EED2Ev
	.section	.text._ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv,"axG",@progbits,_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	.type	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv, @function
_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv:
.LFB6577:
	.cfi_startproc
	endbr64
	vpbroadcastq	.LC29(%rip), %zmm5
	vpbroadcastq	.LC30(%rip), %zmm6
	movq	%rdi, %rcx
	leaq	1248(%rdi), %rax
	vpbroadcastq	.LC31(%rip), %zmm3
	vpbroadcastq	.LC32(%rip), %zmm4
	leaq	1216(%rdi), %rsi
	movq	%rdi, %rdx
	.p2align 4
	.p2align 3
.L365:
	vpandq	8(%rdx), %zmm6, %zmm1
	vpandq	(%rdx), %zmm5, %zmm0
	addq	$64, %rdx
	vporq	%zmm1, %zmm0, %zmm0
	vpsrlq	$1, %zmm0, %zmm1
	vpxorq	1184(%rdx), %zmm1, %zmm1
	vpandq	%zmm3, %zmm0, %zmm0
	vptestnmq	%zmm0, %zmm0, %k1
	vpxorq	%zmm4, %zmm1, %zmm2
	vpblendmq	%zmm1, %zmm2, %zmm0{%k1}
	vmovdqu64	%zmm0, -64(%rdx)
	cmpq	%rdx, %rsi
	jne	.L365
	vpbroadcastq	.LC29(%rip), %ymm0
	vpbroadcastq	.LC30(%rip), %ymm1
	leaq	2464(%rcx), %rdx
	vpand	1224(%rcx), %ymm1, %ymm1
	vpand	1216(%rcx), %ymm0, %ymm0
	vpor	%ymm1, %ymm0, %ymm0
	vpsrlq	$1, %ymm0, %ymm1
	vpxor	2464(%rcx), %ymm1, %ymm1
	vpandq	.LC31(%rip){1to4}, %ymm0, %ymm0
	vptestnmq	%ymm0, %ymm0, %k1
	vpxorq	.LC32(%rip){1to4}, %ymm1, %ymm2
	vpblendmq	%ymm1, %ymm2, %ymm0{%k1}
	vmovdqu	%ymm0, 1216(%rcx)
	.p2align 4
	.p2align 3
.L366:
	vpandq	8(%rax), %zmm6, %zmm1
	addq	$64, %rax
	vpandq	-64(%rax), %zmm5, %zmm0
	vporq	%zmm1, %zmm0, %zmm0
	vpsrlq	$1, %zmm0, %zmm1
	vpxorq	-1312(%rax), %zmm1, %zmm1
	vpandq	%zmm3, %zmm0, %zmm0
	vptestnmq	%zmm0, %zmm0, %k1
	vpxorq	%zmm4, %zmm1, %zmm2
	vpblendmq	%zmm1, %zmm2, %zmm0{%k1}
	vmovdqu64	%zmm0, -64(%rax)
	cmpq	%rdx, %rax
	jne	.L366
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
	je	.L367
	movabsq	$-5403634167711393303, %rax
	xorq	%rax, %rsi
.L367:
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
	je	.L368
	movabsq	$-5403634167711393303, %rdx
	xorq	%rdx, %rsi
.L368:
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
	jne	.L369
.L372:
	movq	(%rcx), %rax
	andq	$-2147483648, %rsi
	movq	%rdx, 2480(%rcx)
	andl	$2147483647, %eax
	orq	%rsi, %rax
	movq	%rax, %rdx
	shrq	%rdx
	xorq	1240(%rcx), %rdx
	testb	$1, %al
	je	.L371
	movabsq	$-5403634167711393303, %rax
	xorq	%rax, %rdx
.L371:
	movq	%rdx, 2488(%rcx)
	movq	$0, 2496(%rcx)
	vzeroupper
	ret
.L369:
	movabsq	$-5403634167711393303, %rax
	xorq	%rax, %rdx
	jmp	.L372
	.cfi_endproc
.LFE6577:
	.size	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv, .-_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	.text
	.align 2
	.p2align 4
	.type	_ZNSt24uniform_int_distributionImEclISt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEEmRT_RKNS0_10param_typeE.constprop.0.isra.0, @function
_ZNSt24uniform_int_distributionImEclISt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEEmRT_RKNS0_10param_typeE.constprop.0.isra.0:
.LFB7547:
	.cfi_startproc
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	movq	%rdx, %r10
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	subq	%rsi, %rdx
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	movq	%rsi, %r12
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rdi, %rbx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	2496(%rdi), %rax
	cmpq	$-1, %rdx
	je	.L382
	movq	%rdx, %rbp
	incq	%rbp
	cmpq	$311, %rax
	ja	.L392
.L383:
	movq	(%rbx,%rax,8), %rsi
	leaq	1(%rax), %rcx
	movabsq	$6148914691236517205, %r13
	movabsq	$8202884508482404352, %r14
	movabsq	$-2270628950310912, %r15
	movq	%rcx, 2496(%rbx)
	movq	%rsi, %rax
	shrq	$29, %rax
	andq	%r13, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$17, %rax
	andq	%r14, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$37, %rax
	andq	%r15, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	shrq	$43, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rdx
	mulx	%rbp, %rsi, %rdi
	cmpq	%rsi, %rbp
	jbe	.L384
	leaq	-1(%r12), %rax
	xorl	%edx, %edx
	subq	%r10, %rax
	divq	%rbp
	movq	%rdx, %r9
	cmpq	%rdx, %rsi
	jb	.L386
	jmp	.L384
	.p2align 4
	.p2align 3
.L385:
	movq	(%rbx,%rax,8), %rsi
	leaq	1(%rax), %rcx
	movq	%rcx, 2496(%rbx)
	movq	%rsi, %rax
	shrq	$29, %rax
	andq	%r13, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$17, %rax
	andq	%r14, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	salq	$37, %rax
	andq	%r15, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rax
	shrq	$43, %rax
	xorq	%rax, %rsi
	movq	%rsi, %rdx
	mulx	%rbp, %rsi, %rdi
	cmpq	%rsi, %r9
	jbe	.L384
.L386:
	movq	%rcx, %rax
	cmpq	$311, %rcx
	jbe	.L385
	movq	%rbx, %rdi
	movq	%r9, 8(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rax
	movq	8(%rsp), %r9
	jmp	.L385
	.p2align 4
	.p2align 3
.L384:
	movq	%rdi, %rax
.L387:
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	addq	%r12, %rax
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
.L392:
	.cfi_restore_state
	movq	%r10, 8(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rax
	movq	8(%rsp), %r10
	jmp	.L383
	.p2align 4
	.p2align 3
.L382:
	cmpq	$311, %rax
	ja	.L393
.L388:
	leaq	1(%rax), %rdx
	movq	(%rbx,%rax,8), %rax
	movabsq	$6148914691236517205, %rcx
	movq	%rdx, 2496(%rbx)
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
	jmp	.L387
	.p2align 4
	.p2align 3
.L393:
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rax
	jmp	.L388
	.cfi_endproc
.LFE7547:
	.size	_ZNSt24uniform_int_distributionImEclISt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEEmRT_RKNS0_10param_typeE.constprop.0.isra.0, .-_ZNSt24uniform_int_distributionImEclISt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEEmRT_RKNS0_10param_typeE.constprop.0.isra.0
	.section	.text._ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_,"axG",@progbits,_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_,comdat
	.p2align 4
	.weak	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_
	.type	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_, @function
_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_:
.LFB6252:
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
	je	.L422
	movq	%rsi, %rcx
	movq	%rdx, %rbx
	movq	%rdi, %r14
	leaq	8(%rdi), %r12
	subq	%rdi, %rcx
	sarq	$3, %rcx
	movq	%rcx, %rax
	mulq	%rcx
	seto	%al
	movzbl	%al, %eax
	testq	%rax, %rax
	je	.L424
	cmpq	%r12, (%rsp)
	je	.L422
	movabsq	$6148914691236517205, %r8
	movabsq	$8202884508482404352, %rbp
	movabsq	$-2270628950310912, %r15
	.p2align 4
	.p2align 3
.L415:
	movq	2496(%rbx), %rdx
	movq	%r12, %rax
	subq	%r14, %rax
	sarq	$3, %rax
	movq	%rdx, %rsi
	cmpq	$-1, %rax
	je	.L408
	leaq	1(%rax), %r13
	cmpq	$311, %rdx
	ja	.L425
.L409:
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
	jbe	.L410
	notq	%rax
	xorl	%edx, %edx
	divq	%r13
	movq	%rdx, %rcx
	cmpq	%rdx, %rsi
	jb	.L412
	jmp	.L410
	.p2align 4
	.p2align 3
.L411:
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
	jbe	.L410
.L412:
	movq	%r9, %rax
	cmpq	$311, %r9
	jbe	.L411
	movq	%rbx, %rdi
	movq	%rcx, 8(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$6148914691236517205, %r8
	movq	2496(%rbx), %rax
	movq	8(%rsp), %rcx
	jmp	.L411
	.p2align 4
	.p2align 3
.L410:
	movq	%rdi, %rax
.L413:
	leaq	(%r14,%rax,8), %rax
	movl	(%r12), %edx
	addq	$8, %r12
	movl	(%rax), %esi
	movl	%esi, -8(%r12)
	movl	%edx, (%rax)
	movl	4(%rax), %esi
	movl	-4(%r12), %edx
	movl	%esi, -4(%r12)
	movl	%edx, 4(%rax)
	cmpq	%r12, (%rsp)
	jne	.L415
.L422:
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
.L408:
	.cfi_restore_state
	cmpq	$311, %rdx
	ja	.L426
.L414:
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
	jmp	.L413
	.p2align 4
	.p2align 3
.L425:
	movq	%rbx, %rdi
	movq	%rax, 8(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$6148914691236517205, %r8
	movq	2496(%rbx), %rdx
	movq	8(%rsp), %rax
	jmp	.L409
	.p2align 4
	.p2align 3
.L426:
	movq	%rbx, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rsi
	movabsq	$6148914691236517205, %r8
	jmp	.L414
	.p2align 4
	.p2align 3
.L424:
	andl	$1, %ecx
	je	.L427
.L399:
	cmpq	%r12, (%rsp)
	je	.L422
	movabsq	$6148914691236517205, %r9
	movabsq	$8202884508482404352, %r8
	movabsq	$-2270628950310912, %rbp
	.p2align 4
	.p2align 3
.L407:
	movq	%r12, %r13
	movq	2496(%rbx), %rax
	subq	%r14, %r13
	sarq	$3, %r13
	leaq	2(%r13), %r15
	incq	%r13
	imulq	%r15, %r13
	testq	%r13, %r13
	je	.L400
	cmpq	$311, %rax
	ja	.L428
.L401:
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
	jbe	.L402
	movq	%r13, %rax
	xorl	%edx, %edx
	negq	%rax
	divq	%r13
	movq	%rdx, %rcx
	cmpq	%rdx, %rsi
	jb	.L404
	jmp	.L402
	.p2align 4
	.p2align 3
.L403:
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
	jbe	.L402
.L404:
	movq	%r11, %rax
	cmpq	$311, %r11
	jbe	.L403
	movq	%rbx, %rdi
	movq	%rcx, 8(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$8202884508482404352, %r8
	movabsq	$6148914691236517205, %r9
	movq	2496(%rbx), %rax
	movq	8(%rsp), %rcx
	jmp	.L403
	.p2align 4
	.p2align 3
.L402:
	movq	%rdi, %rax
.L405:
	xorl	%edx, %edx
	movl	(%r12), %esi
	addq	$16, %r12
	divq	%r15
	leaq	(%r14,%rax,8), %rax
	movl	(%rax), %edi
	movl	%edi, -16(%r12)
	movl	%esi, (%rax)
	movl	4(%rax), %edi
	movl	-12(%r12), %esi
	movl	%edi, -12(%r12)
	movl	%esi, 4(%rax)
	leaq	(%r14,%rdx,8), %rax
	movl	-8(%r12), %edx
	movl	(%rax), %esi
	movl	%esi, -8(%r12)
	movl	%edx, (%rax)
	movl	4(%rax), %esi
	movl	-4(%r12), %edx
	movl	%esi, -4(%r12)
	movl	%edx, 4(%rax)
	cmpq	%r12, (%rsp)
	jne	.L407
	jmp	.L422
	.p2align 4
	.p2align 3
.L400:
	cmpq	$311, %rax
	ja	.L429
.L406:
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
	jmp	.L405
	.p2align 4
	.p2align 3
.L428:
	movq	%rbx, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rax
	movabsq	$8202884508482404352, %r8
	movabsq	$6148914691236517205, %r9
	jmp	.L401
	.p2align 4
	.p2align 3
.L429:
	movq	%rbx, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%rbx), %rax
	movabsq	$8202884508482404352, %r8
	movabsq	$6148914691236517205, %r9
	jmp	.L406
.L427:
	movl	$1, %edx
	xorl	%esi, %esi
	movq	%rbx, %rdi
	leaq	16(%r14), %r12
	call	_ZNSt24uniform_int_distributionImEclISt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEEmRT_RKNS0_10param_typeE.constprop.0.isra.0
	movl	8(%r14), %edx
	leaq	(%r14,%rax,8), %rax
	movl	(%rax), %ecx
	movl	%ecx, 8(%r14)
	movl	%edx, (%rax)
	movl	4(%rax), %ecx
	movl	12(%r14), %edx
	movl	%ecx, 12(%r14)
	movl	%edx, 4(%rax)
	jmp	.L399
	.cfi_endproc
.LFE6252:
	.size	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_, .-_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_
	.section	.text._ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt5arrayIiLm3EESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_,"axG",@progbits,_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt5arrayIiLm3EESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_,comdat
	.p2align 4
	.weak	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt5arrayIiLm3EESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_
	.type	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt5arrayIiLm3EESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_, @function
_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt5arrayIiLm3EESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_:
.LFB6432:
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
	subq	$40, %rsp
	.cfi_def_cfa_offset 96
	movq	%rsi, 8(%rsp)
	cmpq	%rdi, %rsi
	je	.L460
	subq	%rdi, %rsi
	movabsq	$-6148914691236517205, %rax
	movq	%rdx, %r13
	movq	%rdi, %r14
	movq	%rsi, %rcx
	leaq	12(%rdi), %rbx
	sarq	$2, %rcx
	imulq	%rax, %rcx
	movq	%rcx, %rax
	mulq	%rcx
	seto	%al
	movzbl	%al, %eax
	testq	%rax, %rax
	je	.L462
	cmpq	%rbx, 8(%rsp)
	je	.L460
	movabsq	$6148914691236517205, %r9
	movabsq	$8202884508482404352, %rbp
	movabsq	$-2270628950310912, %r12
	movq	%rbx, %r15
	movq	%rdi, (%rsp)
	.p2align 4
	.p2align 3
.L453:
	movq	%r15, %rax
	subq	(%rsp), %rax
	movabsq	$-6148914691236517205, %rbx
	movq	2496(%r13), %rdx
	sarq	$2, %rax
	movq	%rdx, %rcx
	imulq	%rbx, %rax
	cmpq	$-1, %rax
	je	.L446
	leaq	1(%rax), %r14
	cmpq	$311, %rdx
	ja	.L463
.L447:
	movq	0(%r13,%rdx,8), %rcx
	leaq	1(%rdx), %rdi
	movq	%rdi, 2496(%r13)
	movq	%rcx, %rdx
	shrq	$29, %rdx
	andq	%r9, %rdx
	xorq	%rdx, %rcx
	movq	%rcx, %rdx
	salq	$17, %rdx
	andq	%rbp, %rdx
	xorq	%rdx, %rcx
	movq	%rcx, %rdx
	salq	$37, %rdx
	andq	%r12, %rdx
	xorq	%rdx, %rcx
	movq	%rcx, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rcx
	movq	%rcx, %rdx
	mulx	%r14, %rcx, %rbx
	cmpq	%rcx, %r14
	jbe	.L448
	notq	%rax
	xorl	%edx, %edx
	divq	%r14
	movq	%rdx, %rsi
	cmpq	%rdx, %rcx
	jb	.L450
	jmp	.L448
	.p2align 4
	.p2align 3
.L449:
	movq	0(%r13,%rax,8), %rcx
	leaq	1(%rax), %rdi
	movq	%rdi, 2496(%r13)
	movq	%rcx, %rax
	shrq	$29, %rax
	andq	%r9, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$17, %rax
	andq	%rbp, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$37, %rax
	andq	%r12, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	shrq	$43, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rdx
	mulx	%r14, %rcx, %rbx
	cmpq	%rcx, %rsi
	jbe	.L448
.L450:
	movq	%rdi, %rax
	cmpq	$311, %rdi
	jbe	.L449
	movq	%r13, %rdi
	movq	%rsi, 16(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$6148914691236517205, %r9
	movq	2496(%r13), %rax
	movq	16(%rsp), %rsi
	jmp	.L449
	.p2align 4
	.p2align 3
.L448:
	movq	%rbx, %rax
.L451:
	movq	(%rsp), %rbx
	leaq	(%rax,%rax,2), %rax
	movl	(%r15), %edx
	addq	$12, %r15
	leaq	(%rbx,%rax,4), %rax
	movl	(%rax), %ecx
	movl	%ecx, -12(%r15)
	movl	%edx, (%rax)
	movl	4(%rax), %ecx
	movl	-8(%r15), %edx
	movl	%ecx, -8(%r15)
	movl	%edx, 4(%rax)
	movl	8(%rax), %ecx
	movl	-4(%r15), %edx
	movl	%ecx, -4(%r15)
	movl	%edx, 8(%rax)
	cmpq	%r15, 8(%rsp)
	jne	.L453
.L460:
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
.L446:
	.cfi_restore_state
	cmpq	$311, %rdx
	ja	.L464
.L452:
	leaq	1(%rcx), %rax
	movq	%rax, 2496(%r13)
	movq	0(%r13,%rcx,8), %rax
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%r9, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rbp, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%r12, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	jmp	.L451
	.p2align 4
	.p2align 3
.L463:
	movq	%r13, %rdi
	movq	%rax, 16(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$6148914691236517205, %r9
	movq	2496(%r13), %rdx
	movq	16(%rsp), %rax
	jmp	.L447
	.p2align 4
	.p2align 3
.L464:
	movq	%r13, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%r13), %rcx
	movabsq	$6148914691236517205, %r9
	jmp	.L452
.L462:
	andl	$1, %ecx
	je	.L465
.L435:
	cmpq	%rbx, 8(%rsp)
	je	.L460
	movq	%r13, %rsi
	movabsq	$6148914691236517205, %r11
	movabsq	$8202884508482404352, %r12
	movabsq	$-2270628950310912, %rbp
	movq	%rbx, %r13
	movq	%r14, %r15
	.p2align 4
	.p2align 3
.L445:
	movq	%r13, %r14
	movabsq	$-6148914691236517205, %rax
	subq	%r15, %r14
	sarq	$2, %r14
	imulq	%rax, %r14
	movq	2496(%rsi), %rax
	leaq	2(%r14), %r8
	incq	%r14
	imulq	%r8, %r14
	testq	%r14, %r14
	je	.L438
	cmpq	$311, %rax
	ja	.L466
.L439:
	movq	(%rsi,%rax,8), %rcx
	leaq	1(%rax), %r10
	movq	%r10, 2496(%rsi)
	movq	%rcx, %rax
	shrq	$29, %rax
	andq	%r11, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$17, %rax
	andq	%r12, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$37, %rax
	andq	%rbp, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	shrq	$43, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rdx
	mulx	%r14, %rcx, %rbx
	cmpq	%rcx, %r14
	jbe	.L440
	movq	%r14, %rax
	xorl	%edx, %edx
	negq	%rax
	divq	%r14
	cmpq	%rdx, %rcx
	jnb	.L440
	movq	%r13, 16(%rsp)
	movq	%r15, 24(%rsp)
	movq	%r14, %r13
	movq	%r8, (%rsp)
	movq	%rsi, %r14
	movq	%rdx, %r15
	jmp	.L442
	.p2align 4
	.p2align 3
.L441:
	leaq	1(%rax), %r10
	movq	(%r14,%rax,8), %rax
	movq	%r10, 2496(%r14)
	movq	%rax, %rcx
	shrq	$29, %rcx
	andq	%r11, %rcx
	xorq	%rcx, %rax
	movq	%rax, %rcx
	salq	$17, %rcx
	andq	%r12, %rcx
	xorq	%rcx, %rax
	movq	%rax, %rcx
	salq	$37, %rcx
	andq	%rbp, %rcx
	xorq	%rcx, %rax
	movq	%rax, %rcx
	shrq	$43, %rcx
	xorq	%rax, %rcx
	movq	%rcx, %rdx
	mulx	%r13, %rcx, %rbx
	cmpq	%rcx, %r15
	jbe	.L467
.L442:
	movq	%r10, %rax
	cmpq	$311, %r10
	jbe	.L441
	movq	%r14, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496(%r14), %rax
	movabsq	$6148914691236517205, %r11
	jmp	.L441
	.p2align 4
	.p2align 3
.L467:
	movq	(%rsp), %r8
	movq	16(%rsp), %r13
	movq	%r14, %rsi
	movq	24(%rsp), %r15
.L440:
	movq	%rbx, %rax
.L443:
	xorl	%edx, %edx
	movl	0(%r13), %ecx
	addq	$24, %r13
	divq	%r8
	leaq	(%rax,%rax,2), %rax
	leaq	(%r15,%rax,4), %rax
	movl	(%rax), %edi
	movl	%edi, -24(%r13)
	movl	%ecx, (%rax)
	movl	4(%rax), %edi
	movl	-20(%r13), %ecx
	movl	%edi, -20(%r13)
	movl	%ecx, 4(%rax)
	movl	8(%rax), %edi
	movl	-16(%r13), %ecx
	movl	%edi, -16(%r13)
	movl	%ecx, 8(%rax)
	leaq	(%rdx,%rdx,2), %rax
	movl	-12(%r13), %edx
	leaq	(%r15,%rax,4), %rax
	movl	(%rax), %ecx
	movl	%ecx, -12(%r13)
	movl	%edx, (%rax)
	movl	4(%rax), %ecx
	movl	-8(%r13), %edx
	movl	%ecx, -8(%r13)
	movl	%edx, 4(%rax)
	movl	8(%rax), %ecx
	movl	-4(%r13), %edx
	movl	%ecx, -4(%r13)
	movl	%edx, 8(%rax)
	cmpq	%r13, 8(%rsp)
	jne	.L445
	jmp	.L460
	.p2align 4
	.p2align 3
.L438:
	cmpq	$311, %rax
	ja	.L468
.L444:
	leaq	1(%rax), %rdx
	movq	(%rsi,%rax,8), %rax
	movq	%rdx, 2496(%rsi)
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%r11, %rdx
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
	jmp	.L443
	.p2align 4
	.p2align 3
.L466:
	movq	%rsi, %rdi
	movq	%r8, 16(%rsp)
	movq	%rsi, (%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$6148914691236517205, %r11
	movq	(%rsp), %rsi
	movq	16(%rsp), %r8
	movq	2496(%rsi), %rax
	jmp	.L439
.L468:
	movq	%rsi, %rdi
	movq	%r8, 16(%rsp)
	movq	%rsi, (%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movabsq	$6148914691236517205, %r11
	movq	(%rsp), %rsi
	movq	16(%rsp), %r8
	movq	2496(%rsi), %rax
	jmp	.L444
.L465:
	movl	$1, %edx
	xorl	%esi, %esi
	movq	%r13, %rdi
	leaq	24(%r14), %rbx
	call	_ZNSt24uniform_int_distributionImEclISt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEEmRT_RKNS0_10param_typeE.constprop.0.isra.0
	leaq	19(%r14), %rdx
	leaq	(%rax,%rax,2), %rax
	leaq	(%r14,%rax,4), %rax
	subq	%rax, %rdx
	cmpq	$14, %rdx
	jbe	.L436
	movq	12(%r14), %rdx
	movq	(%rax), %rcx
	movq	%rcx, 12(%r14)
	movq	%rdx, (%rax)
	movl	8(%rax), %ecx
	movl	20(%r14), %edx
	movl	%ecx, 20(%r14)
	movl	%edx, 8(%rax)
	jmp	.L435
.L436:
	movl	12(%r14), %edx
	movl	(%rax), %ecx
	movl	%ecx, 12(%r14)
	movl	%edx, (%rax)
	movl	4(%rax), %ecx
	movl	16(%r14), %edx
	movl	%ecx, 16(%r14)
	movl	%edx, 4(%rax)
	movl	8(%rax), %ecx
	movl	20(%r14), %edx
	movl	%ecx, 20(%r14)
	movl	%edx, 8(%rax)
	jmp	.L435
	.cfi_endproc
.LFE6432:
	.size	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt5arrayIiLm3EESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_, .-_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt5arrayIiLm3EESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_
	.text
	.p2align 4
	.globl	_Z7randinti
	.type	_Z7randinti, @function
_Z7randinti:
.LFB5625:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	leaq	rng(%rip), %rbp
	movslq	%edi, %rbx
	subq	$8, %rsp
	.cfi_def_cfa_offset 32
	movq	2496+rng(%rip), %rax
	cmpq	$311, %rax
	ja	.L472
.L470:
	leaq	1(%rax), %rdx
	movq	0(%rbp,%rax,8), %rax
	movabsq	$6148914691236517205, %rcx
	movq	%rdx, 2496+rng(%rip)
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
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
	xorl	%edx, %edx
	divq	%rbx
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	movl	%edx, %eax
	ret
	.p2align 4
	.p2align 3
.L472:
	.cfi_restore_state
	movq	%rbp, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rax
	jmp	.L470
	.cfi_endproc
.LFE5625:
	.size	_Z7randinti, .-_Z7randinti
	.p2align 4
	.globl	_Z9uniform01v
	.type	_Z9uniform01v, @function
_Z9uniform01v:
.LFB5626:
	.cfi_startproc
	endbr64
	movq	2496+rng(%rip), %rax
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset 3, -16
	leaq	rng(%rip), %rbx
	cmpq	$311, %rax
	ja	.L476
.L474:
	leaq	1(%rax), %rdx
	movq	(%rbx,%rax,8), %rax
	movabsq	$6148914691236517205, %rcx
	vxorps	%xmm0, %xmm0, %xmm0
	movq	%rdx, 2496+rng(%rip)
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 8
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
	shrq	$11, %rax
	vcvtsi2sdq	%rax, %xmm0, %xmm0
	vmulsd	.LC33(%rip), %xmm0, %xmm0
	ret
	.p2align 4
	.p2align 3
.L476:
	.cfi_restore_state
	movq	%rbx, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rax
	jmp	.L474
	.cfi_endproc
.LFE5626:
	.size	_Z9uniform01v, .-_Z9uniform01v
	.section	.rodata._ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm.str1.1,"aMS",@progbits,1
.LC34:
	.string	"vector::_M_default_append"
	.section	.text._ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm,"axG",@progbits,_ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm
	.type	_ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm, @function
_ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm:
.LFB6701:
	.cfi_startproc
	endbr64
	testq	%rsi, %rsi
	je	.L504
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movabsq	$5675921253449092805, %rcx
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rsi, %rbp
	subq	$8, %rsp
	.cfi_def_cfa_offset 64
	movq	8(%rdi), %r8
	movq	(%rdi), %r10
	movabsq	$88686269585142075, %rdx
	movq	16(%rdi), %rsi
	movq	%rdi, %r12
	movq	%r8, %rbx
	subq	%r10, %rbx
	movq	%rsi, %rax
	movq	%rbx, %r13
	subq	%r8, %rax
	sarq	$3, %r13
	sarq	$3, %rax
	imulq	%rcx, %r13
	imulq	%rcx, %rax
	subq	%r13, %rdx
	cmpq	%rax, %rbp
	ja	.L479
	movq	%rbp, %rsi
	movq	%r8, %rdx
	xorl	%eax, %eax
	vpxor	%xmm0, %xmm0, %xmm0
	.p2align 4
	.p2align 3
.L480:
	movq	%rdx, %rdi
	movl	$13, %ecx
	addq	$104, %rdx
	rep stosq
	vmovdqu	%xmm0, -24(%rdx)
	decq	%rsi
	jne	.L480
	imulq	$104, %rbp, %rbp
	addq	%r8, %rbp
	movq	%rbp, 8(%r12)
	addq	$8, %rsp
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
.L504:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L479:
	.cfi_def_cfa_offset 64
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	cmpq	%rbp, %rdx
	jb	.L507
	cmpq	%r13, %rbp
	movq	%r13, %r14
	cmovnb	%rbp, %r14
	addq	%r13, %r14
	jc	.L483
	testq	%r14, %r14
	jne	.L508
	xorl	%r14d, %r14d
	xorl	%r15d, %r15d
.L485:
	addq	%r15, %rbx
	movq	%rbp, %r9
	xorl	%eax, %eax
	vpxor	%xmm0, %xmm0, %xmm0
	.p2align 4
	.p2align 3
.L486:
	movq	%rbx, %rdi
	movl	$13, %ecx
	addq	$104, %rbx
	rep stosq
	vmovdqu	%xmm0, -24(%rbx)
	decq	%r9
	jne	.L486
	movq	%r10, %rax
	movq	%r15, %rdx
	cmpq	%r8, %r10
	je	.L490
	.p2align 4
	.p2align 3
.L487:
	vmovdqu	(%rax), %xmm2
	vmovdqu	16(%rax), %xmm3
	addq	$104, %rax
	addq	$104, %rdx
	vmovdqu	-72(%rax), %xmm4
	vmovdqu	-56(%rax), %xmm5
	vmovdqu	-40(%rax), %xmm6
	vmovdqu	-24(%rax), %xmm7
	movq	-8(%rax), %rcx
	movq	%rcx, -8(%rdx)
	vmovdqu	%xmm2, -104(%rdx)
	vmovdqu	%xmm3, -88(%rdx)
	vmovdqu	%xmm4, -72(%rdx)
	vmovdqu	%xmm5, -56(%rdx)
	vmovdqu	%xmm6, -40(%rdx)
	vmovdqu	%xmm7, -24(%rdx)
	cmpq	%r8, %rax
	jne	.L487
.L490:
	testq	%r10, %r10
	je	.L489
	subq	%r10, %rsi
	movq	%r10, %rdi
	call	_ZdlPvm@PLT
.L489:
	addq	%rbp, %r13
	vmovq	%r15, %xmm1
	movq	%r14, 16(%r12)
	imulq	$104, %r13, %r13
	addq	%r15, %r13
	vpinsrq	$1, %r13, %xmm1, %xmm0
	vmovdqu	%xmm0, (%r12)
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
.L508:
	.cfi_restore_state
	movabsq	$88686269585142075, %rax
	cmpq	%rax, %r14
	cmova	%rax, %r14
	imulq	$104, %r14, %r14
.L484:
	movq	%r14, %rdi
	call	_Znwm@PLT
	movq	8(%r12), %r8
	movq	(%r12), %r10
	movq	16(%r12), %rsi
	movq	%rax, %r15
	addq	%rax, %r14
	jmp	.L485
.L483:
	movabsq	$9223372036854775800, %r14
	jmp	.L484
.L507:
	leaq	.LC34(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE6701:
	.size	_ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm, .-_ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm
	.section	.rodata.str1.1
.LC35:
	.string	".txt"
.LC36:
	.string	".json"
.LC37:
	.string	"{\"family\":\""
.LC38:
	.string	"\",\"layers\":["
.LC39:
	.string	"]}\n"
.LC40:
	.string	"{\"local\":["
.LC41:
	.string	"],\"cx\":["
.LC42:
	.string	"]}"
	.section	.text.unlikely,"ax",@progbits
.LCOLDB44:
	.text
.LHOTB44:
	.p2align 4
	.globl	_Z4saveRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE
	.type	_Z4saveRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE, @function
_Z4saveRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE:
.LFB5703:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5703
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
	movq	%rsi, %r12
	andq	$-32, %rsp
	subq	$1216, %rsp
	movq	(%rsi), %r14
	movq	8(%rsi), %r13
	movq	%rdi, 40(%rsp)
	leaq	688(%rsp), %rbx
	movq	%fs:40, %rax
	movq	%rax, 1208(%rsp)
	xorl	%eax, %eax
	movq	%r14, %rax
	movq	%rbx, 672(%rsp)
	addq	%r13, %rax
	je	.L510
	testq	%r14, %r14
	je	.L615
.L510:
	movq	%r13, 120(%rsp)
	cmpq	$15, %r13
	ja	.L616
	cmpq	$1, %r13
	jne	.L513
	movzbl	(%r14), %eax
	movb	%al, 688(%rsp)
	movq	%rbx, %rax
.L514:
	movq	%r13, 680(%rsp)
	movb	$0, (%rax,%r13)
	movabsq	$4611686018427387903, %rax
	subq	680(%rsp), %rax
	cmpq	$3, %rax
	jbe	.L617
	leaq	672(%rsp), %r13
	movl	$4, %edx
	leaq	.LC35(%rip), %rsi
	movq	%r13, %rdi
.LEHB4:
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_appendEPKcm@PLT
.LEHE4:
	leaq	408(%rsp), %rax
	leaq	160(%rsp), %r15
	movq	%rax, %rdi
	movq	%rax, 32(%rsp)
	movq	%r15, 88(%rsp)
	call	_ZNSt8ios_baseC2Ev@PLT
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movw	$0, 632(%rsp)
	movq	%rax, 408(%rsp)
	movq	8+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	vmovdqa	%ymm0, 640(%rsp)
	xorl	%esi, %esi
	movq	$0, 624(%rsp)
	movq	-24(%rax), %rdi
	movq	%rax, 160(%rsp)
	movq	16+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	addq	%r15, %rdi
	movq	%rax, (%rdi)
	vzeroupper
.LEHB5:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE4initEPSt15basic_streambufIcS1_E@PLT
.LEHE5:
	leaq	24+_ZTVSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	%rax, 160(%rsp)
	addq	$40, %rax
	movq	%rax, 408(%rsp)
	leaq	168(%rsp), %rax
	movq	%rax, %rdi
	movq	%rax, %r14
	movq	%rax, 16(%rsp)
.LEHB6:
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEEC1Ev@PLT
.LEHE6:
	movq	32(%rsp), %rdi
	movq	%r14, %rsi
.LEHB7:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE4initEPSt15basic_streambufIcS1_E@PLT
	movq	672(%rsp), %rsi
	movq	16(%rsp), %rdi
	movl	$16, %edx
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEE4openEPKcSt13_Ios_Openmode@PLT
	movq	160(%rsp), %rdx
	movq	-24(%rdx), %rdi
	addq	%r15, %rdi
	testq	%rax, %rax
	je	.L618
	xorl	%esi, %esi
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE5clearESt12_Ios_Iostate@PLT
.LEHE7:
.L520:
	movq	672(%rsp), %rdi
	cmpq	%rbx, %rdi
	je	.L522
	movq	688(%rsp), %rax
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
.L522:
	movl	nq(%rip), %esi
	movq	88(%rsp), %rdi
.LEHB8:
	call	_ZNSolsEi@PLT
	movq	%rax, %rdi
	leaq	107(%rsp), %rsi
	movl	$1, %edx
	movb	$32, 107(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movl	rounds(%rip), %esi
	movq	%rax, %rdi
	call	_ZNSolsEi@PLT
	movq	%rax, %rdi
	leaq	108(%rsp), %rsi
	movl	$1, %edx
	movb	$10, 108(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
.LEHE8:
	movq	(%r12), %r14
	leaq	144(%rsp), %rbx
	movq	8(%r12), %r12
	movq	%rbx, 128(%rsp)
	movq	%r14, %rax
	addq	%r12, %rax
	je	.L528
	testq	%r14, %r14
	je	.L619
.L528:
	movq	%r12, 120(%rsp)
	cmpq	$15, %r12
	ja	.L620
	cmpq	$1, %r12
	jne	.L531
	movzbl	(%r14), %eax
	movb	%al, 144(%rsp)
	movq	%rbx, %rax
.L532:
	movq	%r12, 136(%rsp)
	movb	$0, (%rax,%r12)
	movabsq	$4611686018427387903, %rax
	subq	136(%rsp), %rax
	cmpq	$4, %rax
	jbe	.L621
	leaq	128(%rsp), %rdi
	movl	$5, %edx
	leaq	.LC36(%rip), %rsi
.LEHB9:
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_appendEPKcm@PLT
.LEHE9:
	leaq	920(%rsp), %rax
	movq	%rax, %rdi
	movq	%rax, %r14
	movq	%rax, 8(%rsp)
	call	_ZNSt8ios_baseC2Ev@PLT
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movw	$0, 1144(%rsp)
	movq	%rax, 920(%rsp)
	movq	8+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	vmovdqa	%ymm0, 1152(%rsp)
	xorl	%esi, %esi
	movq	$0, 1136(%rsp)
	movq	-24(%rax), %rdi
	movq	%rax, 672(%rsp)
	movq	16+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	addq	%r13, %rdi
	movq	%rax, (%rdi)
	vzeroupper
.LEHB10:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE4initEPSt15basic_streambufIcS1_E@PLT
.LEHE10:
	leaq	24+_ZTVSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	%rax, 672(%rsp)
	addq	$40, %rax
	movq	%rax, 920(%rsp)
	leaq	680(%rsp), %rax
	movq	%rax, %rdi
	movq	%rax, %r15
	movq	%rax, 24(%rsp)
.LEHB11:
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEEC1Ev@PLT
.LEHE11:
	movq	%r15, %rsi
	movq	%r14, %rdi
.LEHB12:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE4initEPSt15basic_streambufIcS1_E@PLT
	movq	128(%rsp), %rsi
	movq	24(%rsp), %rdi
	movl	$16, %edx
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEE4openEPKcSt13_Ios_Openmode@PLT
	movq	672(%rsp), %rdx
	movq	-24(%rdx), %rdi
	addq	%r13, %rdi
	testq	%rax, %rax
	je	.L622
	xorl	%esi, %esi
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE5clearESt12_Ios_Iostate@PLT
.LEHE12:
.L539:
	movq	128(%rsp), %rdi
	cmpq	%rbx, %rdi
	je	.L541
	movq	144(%rsp), %rax
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
.L541:
	movl	$11, %edx
	leaq	.LC37(%rip), %rsi
	movq	%r13, %rdi
.LEHB13:
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	8+_Z6familyB5cxx11(%rip), %rdx
	movq	_Z6familyB5cxx11(%rip), %rsi
	movq	%r13, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	%rax, %rdi
	movl	$12, %edx
	leaq	.LC38(%rip), %rsi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movl	rounds(%rip), %edx
	testl	%edx, %edx
	jle	.L558
	movq	40(%rsp), %rax
	movq	$104, 48(%rsp)
	movl	$0, 60(%rsp)
	movq	(%rax), %r12
	leaq	115(%rsp), %rax
	movq	%rax, 80(%rsp)
	.p2align 4
	.p2align 3
.L564:
	movl	$10, %edx
	leaq	.LC40(%rip), %rsi
	movq	%r13, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movl	nq(%rip), %eax
	xorl	%ebx, %ebx
	testl	%eax, %eax
	jle	.L552
	.p2align 4
	.p2align 3
.L549:
	movl	(%r12,%rbx,4), %esi
	movq	88(%rsp), %rdi
	call	_ZNSolsEi@PLT
	movq	%rax, %rdi
	leaq	110(%rsp), %rsi
	movl	$1, %edx
	movb	$32, 110(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	testq	%rbx, %rbx
	je	.L551
	leaq	111(%rsp), %rsi
	movl	$1, %edx
	movq	%r13, %rdi
	movb	$44, 111(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
.L551:
	leaq	112(%rsp), %rsi
	movl	$1, %edx
	movq	%r13, %rdi
	movb	$34, 112(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movslq	(%r12,%rbx,4), %rcx
	movq	%rax, %rdi
	leaq	_ZL5words(%rip), %rax
	salq	$5, %rcx
	addq	%rax, %rcx
	movq	8(%rcx), %rdx
	movq	(%rcx), %rsi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	%rax, %rdi
	leaq	113(%rsp), %rsi
	movl	$1, %edx
	movb	$34, 113(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	incq	%rbx
	cmpl	%ebx, nq(%rip)
	jg	.L549
.L552:
	movq	88(%r12), %rsi
	subq	80(%r12), %rsi
	movq	88(%rsp), %rdi
	sarq	$3, %rsi
	call	_ZNSo9_M_insertImEERSoT_@PLT
	movl	$8, %edx
	leaq	.LC41(%rip), %rsi
	movq	%r13, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	80(%r12), %rdx
	movq	88(%r12), %rax
	leaq	114(%rsp), %rcx
	xorl	%ebx, %ebx
	movq	%rcx, 64(%rsp)
	subq	%rdx, %rax
	sarq	$3, %rax
	testl	%eax, %eax
	jle	.L556
	.p2align 4
	.p2align 3
.L553:
	movq	64(%rsp), %rsi
	movq	88(%rsp), %rdi
	leaq	(%rdx,%rbx,8), %rax
	movl	$1, %edx
	movl	(%rax), %r15d
	movl	4(%rax), %r14d
	movb	$32, 114(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	%rax, %rdi
	movl	%r15d, %esi
	call	_ZNSolsEi@PLT
	movq	80(%rsp), %rsi
	movq	%rax, %rdi
	movl	$1, %edx
	movb	$32, 115(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	%rax, %rdi
	movl	%r14d, %esi
	call	_ZNSolsEi@PLT
	testq	%rbx, %rbx
	je	.L555
	leaq	116(%rsp), %rsi
	movl	$1, %edx
	movq	%r13, %rdi
	movb	$44, 116(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
.L555:
	leaq	117(%rsp), %rsi
	movl	$1, %edx
	movq	%r13, %rdi
	movb	$91, 117(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	%rax, %rdi
	movl	%r15d, %esi
	call	_ZNSolsEi@PLT
	movq	%rax, %rdi
	leaq	118(%rsp), %rsi
	movl	$1, %edx
	movb	$44, 118(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	%rax, %rdi
	movl	%r14d, %esi
	call	_ZNSolsEi@PLT
	movq	%rax, %rdi
	leaq	119(%rsp), %rsi
	movl	$1, %edx
	movb	$93, 119(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	80(%r12), %rdx
	incq	%rbx
	movq	88(%r12), %rax
	subq	%rdx, %rax
	sarq	$3, %rax
	cmpl	%ebx, %eax
	jg	.L553
.L556:
	movq	88(%rsp), %rdi
	leaq	120(%rsp), %rsi
	movl	$1, %edx
	movb	$10, 120(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movl	$2, %edx
	leaq	.LC42(%rip), %rsi
	movq	%r13, %rdi
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	incl	60(%rsp)
	movl	60(%rsp), %eax
	cmpl	%eax, rounds(%rip)
	jle	.L558
	movq	40(%rsp), %rax
	movq	48(%rsp), %rbx
	leaq	109(%rsp), %rsi
	movl	$1, %edx
	movq	%r13, %rdi
	movb	$44, 109(%rsp)
	movq	(%rax), %r12
	addq	%rbx, %r12
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	addq	$104, %rbx
	movq	%rbx, 48(%rsp)
	jmp	.L564
.L513:
	testq	%r13, %r13
	jne	.L623
	movq	%rbx, %rax
	jmp	.L514
	.p2align 4
	.p2align 3
.L558:
	vmovq	.LC43(%rip), %xmm2
	leaq	16+_ZTVSt13basic_filebufIcSt11char_traitsIcEE(%rip), %rax
	movl	$3, %edx
	leaq	.LC39(%rip), %rsi
	movq	%r13, %rdi
	vpinsrq	$1, %rax, %xmm2, %xmm1
	vmovdqa	%xmm1, 64(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
.LEHE13:
	vmovdqa	64(%rsp), %xmm3
	leaq	64+_ZTVSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	24(%rsp), %rdi
	movq	%rax, 920(%rsp)
	vmovdqa	%xmm3, 672(%rsp)
.LEHB14:
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEE5closeEv@PLT
.LEHE14:
.L561:
	leaq	784(%rsp), %rdi
	leaq	16+_ZTVSt15basic_streambufIcSt11char_traitsIcEE(%rip), %rbx
	call	_ZNSt12__basic_fileIcED1Ev@PLT
	leaq	736(%rsp), %rdi
	movq	%rbx, 680(%rsp)
	call	_ZNSt6localeD1Ev@PLT
	movq	8+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	16+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rcx
	movq	8(%rsp), %rdi
	movq	%rax, 672(%rsp)
	movq	-24(%rax), %rax
	movq	%rcx, 672(%rsp,%rax)
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	movq	%rax, 920(%rsp)
	call	_ZNSt8ios_baseD2Ev@PLT
	leaq	64+_ZTVSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	vmovdqa	64(%rsp), %xmm4
	movq	%rax, 408(%rsp)
	movq	16(%rsp), %rdi
	vmovdqa	%xmm4, 160(%rsp)
.LEHB15:
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEE5closeEv@PLT
.LEHE15:
.L559:
	leaq	272(%rsp), %rdi
	call	_ZNSt12__basic_fileIcED1Ev@PLT
	leaq	224(%rsp), %rdi
	movq	%rbx, 168(%rsp)
	call	_ZNSt6localeD1Ev@PLT
	movq	8+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	16+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rcx
	movq	32(%rsp), %rdi
	movq	%rax, 160(%rsp)
	movq	-24(%rax), %rax
	movq	%rcx, 160(%rsp,%rax)
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	movq	%rax, 408(%rsp)
	call	_ZNSt8ios_baseD2Ev@PLT
	movq	1208(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L624
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
.L531:
	.cfi_restore_state
	testq	%r12, %r12
	jne	.L625
	movq	%rbx, %rax
	jmp	.L532
.L620:
	leaq	120(%rsp), %rsi
	leaq	128(%rsp), %rdi
	xorl	%edx, %edx
.LEHB16:
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_createERmm@PLT
.LEHE16:
	movq	%rax, %rdi
	movq	%rax, 128(%rsp)
	movq	120(%rsp), %rax
	movq	%rax, 144(%rsp)
.L530:
	movq	%r12, %rdx
	movq	%r14, %rsi
	call	memcpy@PLT
	movq	120(%rsp), %r12
	movq	128(%rsp), %rax
	jmp	.L532
.L616:
	leaq	672(%rsp), %rdi
	leaq	120(%rsp), %rsi
	xorl	%edx, %edx
.LEHB17:
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_createERmm@PLT
.LEHE17:
	movq	%rax, %rdi
	movq	%rax, 672(%rsp)
	movq	120(%rsp), %rax
	movq	%rax, 688(%rsp)
.L512:
	movq	%r13, %rdx
	movq	%r14, %rsi
	call	memcpy@PLT
	movq	120(%rsp), %r13
	movq	672(%rsp), %rax
	jmp	.L514
.L618:
	movl	32(%rdi), %esi
	orl	$4, %esi
.LEHB18:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE5clearESt12_Ios_Iostate@PLT
.LEHE18:
	jmp	.L520
.L622:
	movl	32(%rdi), %esi
	orl	$4, %esi
.LEHB19:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE5clearESt12_Ios_Iostate@PLT
.LEHE19:
	jmp	.L539
.L617:
	leaq	.LC20(%rip), %rdi
.LEHB20:
	call	_ZSt20__throw_length_errorPKc@PLT
.LEHE20:
.L619:
	leaq	.LC0(%rip), %rdi
.LEHB21:
	call	_ZSt19__throw_logic_errorPKc@PLT
.LEHE21:
.L621:
	leaq	.LC20(%rip), %rdi
.LEHB22:
	call	_ZSt20__throw_length_errorPKc@PLT
.LEHE22:
.L623:
	movq	%rbx, %rdi
	jmp	.L512
.L624:
	call	__stack_chk_fail@PLT
.L625:
	movq	%rbx, %rdi
	jmp	.L530
.L615:
	leaq	.LC0(%rip), %rdi
.LEHB23:
	call	_ZSt19__throw_logic_errorPKc@PLT
.LEHE23:
.L575:
	endbr64
	movq	%rax, %r12
	jmp	.L517
.L572:
	endbr64
	movq	%rax, %r12
	vzeroupper
	jmp	.L525
.L579:
	endbr64
	movq	%rax, %r12
	jmp	.L542
.L571:
	endbr64
	movq	%rax, %r12
	jmp	.L563
.L573:
	endbr64
	movq	%rax, %r12
	vzeroupper
	jmp	.L524
.L570:
	endbr64
	movq	%rax, %r12
	vzeroupper
	jmp	.L537
.L580:
	endbr64
	movq	%rax, %rdi
	jmp	.L560
.L581:
	endbr64
	movq	%rax, %rdi
	jmp	.L562
.L574:
	endbr64
	movq	%rax, %r12
	jmp	.L523
.L577:
	endbr64
	movq	%rax, %r12
	vzeroupper
	jmp	.L544
.L576:
	endbr64
	movq	%rax, %r12
	jmp	.L535
.L578:
	endbr64
	movq	%rax, %r12
	vzeroupper
	jmp	.L543
	.section	.gcc_except_table,"a",@progbits
	.align 4
.LLSDA5703:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATT5703-.LLSDATTD5703
.LLSDATTD5703:
	.byte	0x1
	.uleb128 .LLSDACSE5703-.LLSDACSB5703
.LLSDACSB5703:
	.uleb128 .LEHB4-.LFB5703
	.uleb128 .LEHE4-.LEHB4
	.uleb128 .L575-.LFB5703
	.uleb128 0
	.uleb128 .LEHB5-.LFB5703
	.uleb128 .LEHE5-.LEHB5
	.uleb128 .L572-.LFB5703
	.uleb128 0
	.uleb128 .LEHB6-.LFB5703
	.uleb128 .LEHE6-.LEHB6
	.uleb128 .L573-.LFB5703
	.uleb128 0
	.uleb128 .LEHB7-.LFB5703
	.uleb128 .LEHE7-.LEHB7
	.uleb128 .L574-.LFB5703
	.uleb128 0
	.uleb128 .LEHB8-.LFB5703
	.uleb128 .LEHE8-.LEHB8
	.uleb128 .L570-.LFB5703
	.uleb128 0
	.uleb128 .LEHB9-.LFB5703
	.uleb128 .LEHE9-.LEHB9
	.uleb128 .L576-.LFB5703
	.uleb128 0
	.uleb128 .LEHB10-.LFB5703
	.uleb128 .LEHE10-.LEHB10
	.uleb128 .L577-.LFB5703
	.uleb128 0
	.uleb128 .LEHB11-.LFB5703
	.uleb128 .LEHE11-.LEHB11
	.uleb128 .L578-.LFB5703
	.uleb128 0
	.uleb128 .LEHB12-.LFB5703
	.uleb128 .LEHE12-.LEHB12
	.uleb128 .L579-.LFB5703
	.uleb128 0
	.uleb128 .LEHB13-.LFB5703
	.uleb128 .LEHE13-.LEHB13
	.uleb128 .L571-.LFB5703
	.uleb128 0
	.uleb128 .LEHB14-.LFB5703
	.uleb128 .LEHE14-.LEHB14
	.uleb128 .L580-.LFB5703
	.uleb128 0x1
	.uleb128 .LEHB15-.LFB5703
	.uleb128 .LEHE15-.LEHB15
	.uleb128 .L581-.LFB5703
	.uleb128 0x1
	.uleb128 .LEHB16-.LFB5703
	.uleb128 .LEHE16-.LEHB16
	.uleb128 .L570-.LFB5703
	.uleb128 0
	.uleb128 .LEHB17-.LFB5703
	.uleb128 .LEHE17-.LEHB17
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB18-.LFB5703
	.uleb128 .LEHE18-.LEHB18
	.uleb128 .L574-.LFB5703
	.uleb128 0
	.uleb128 .LEHB19-.LFB5703
	.uleb128 .LEHE19-.LEHB19
	.uleb128 .L579-.LFB5703
	.uleb128 0
	.uleb128 .LEHB20-.LFB5703
	.uleb128 .LEHE20-.LEHB20
	.uleb128 .L575-.LFB5703
	.uleb128 0
	.uleb128 .LEHB21-.LFB5703
	.uleb128 .LEHE21-.LEHB21
	.uleb128 .L570-.LFB5703
	.uleb128 0
	.uleb128 .LEHB22-.LFB5703
	.uleb128 .LEHE22-.LEHB22
	.uleb128 .L576-.LFB5703
	.uleb128 0
	.uleb128 .LEHB23-.LFB5703
	.uleb128 .LEHE23-.LEHB23
	.uleb128 0
	.uleb128 0
.LLSDACSE5703:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATT5703:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC5703
	.type	_Z4saveRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold, @function
_Z4saveRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold:
.LFSB5703:
.L517:
	.cfi_def_cfa 6, 16
	.cfi_offset 3, -56
	.cfi_offset 6, -16
	.cfi_offset 12, -48
	.cfi_offset 13, -40
	.cfi_offset 14, -32
	.cfi_offset 15, -24
	movq	672(%rsp), %rdi
	cmpq	%rbx, %rdi
	je	.L610
	movq	688(%rsp), %rax
	leaq	1(%rax), %rsi
	vzeroupper
	call	_ZdlPvm@PLT
.L614:
	movq	%r12, %rdi
.LEHB24:
	call	_Unwind_Resume@PLT
.LEHE24:
.L523:
	movq	16(%rsp), %rdi
	vzeroupper
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEED1Ev@PLT
.L524:
	movq	8+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	16+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rcx
	movq	%rax, 160(%rsp)
	movq	-24(%rax), %rax
	movq	%rcx, 160(%rsp,%rax)
.L525:
	movq	32(%rsp), %rdi
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	movq	%rax, 408(%rsp)
	call	_ZNSt8ios_baseD2Ev@PLT
	movq	672(%rsp), %rdi
	cmpq	%rbx, %rdi
	je	.L614
	movq	688(%rsp), %rax
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
	jmp	.L614
.L610:
	vzeroupper
	jmp	.L614
.L542:
	movq	24(%rsp), %rdi
	vzeroupper
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEED1Ev@PLT
.L543:
	movq	8+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	16+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rcx
	movq	%rax, 672(%rsp)
	movq	-24(%rax), %rax
	movq	%rcx, 672(%rsp,%rax)
.L544:
	movq	8(%rsp), %rdi
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	movq	%rax, 920(%rsp)
	call	_ZNSt8ios_baseD2Ev@PLT
	movq	128(%rsp), %rdi
	cmpq	%rbx, %rdi
	je	.L537
	movq	144(%rsp), %rax
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
	jmp	.L537
.L563:
	movq	%r13, %rdi
	vzeroupper
	call	_ZNSt14basic_ofstreamIcSt11char_traitsIcEED1Ev@PLT
.L537:
	movq	88(%rsp), %rdi
	call	_ZNSt14basic_ofstreamIcSt11char_traitsIcEED1Ev@PLT
	jmp	.L614
.L560:
	vzeroupper
	call	__cxa_begin_catch@PLT
	call	__cxa_end_catch@PLT
	jmp	.L561
.L562:
	vzeroupper
	call	__cxa_begin_catch@PLT
	call	__cxa_end_catch@PLT
	jmp	.L559
.L535:
	movq	128(%rsp), %rdi
	cmpq	%rbx, %rdi
	je	.L611
	movq	144(%rsp), %rax
	leaq	1(%rax), %rsi
	vzeroupper
	call	_ZdlPvm@PLT
	jmp	.L537
.L611:
	vzeroupper
	jmp	.L537
	.cfi_endproc
.LFE5703:
	.section	.gcc_except_table
	.align 4
.LLSDAC5703:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATTC5703-.LLSDATTDC5703
.LLSDATTDC5703:
	.byte	0x1
	.uleb128 .LLSDACSEC5703-.LLSDACSBC5703
.LLSDACSBC5703:
	.uleb128 .LEHB24-.LCOLDB44
	.uleb128 .LEHE24-.LEHB24
	.uleb128 0
	.uleb128 0
.LLSDACSEC5703:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATTC5703:
	.section	.text.unlikely
	.text
	.size	_Z4saveRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE, .-_Z4saveRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE
	.section	.text.unlikely
	.size	_Z4saveRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold, .-_Z4saveRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold
.LCOLDE44:
	.text
.LHOTE44:
	.section	.rodata._ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_.str1.1,"aMS",@progbits,1
.LC45:
	.string	"vector::_M_realloc_insert"
	.section	.text._ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,"axG",@progbits,_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.type	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, @function
_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_:
.LFB6764:
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
	movabsq	$1152921504606846975, %rcx
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
	sarq	$3, %rax
	cmpq	%rcx, %rax
	je	.L645
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
	jne	.L637
	testq	%rax, %rax
	jne	.L631
	movl	$8, %ecx
	xorl	%ebx, %ebx
	xorl	%r15d, %r15d
.L636:
	movq	(%rdx), %rax
	movq	%rax, (%r15,%rsi)
	cmpq	%r12, %rbp
	je	.L632
	movq	%rbp, %rsi
	movq	%r15, %rdx
	movq	%r12, %rax
	subq	%r12, %rsi
	.p2align 4
	.p2align 3
.L633:
	movq	(%rax), %rcx
	addq	$8, %rax
	addq	$8, %rdx
	movq	%rcx, -8(%rdx)
	cmpq	%rbp, %rax
	jne	.L633
	leaq	8(%r15,%rsi), %rcx
.L632:
	cmpq	%r14, %rbp
	je	.L634
	subq	%rbp, %r14
	movq	%rcx, %rdi
	movq	%rbp, %rsi
	movq	%r14, %rdx
	call	memcpy@PLT
	movq	%rax, %rcx
	addq	%r14, %rcx
.L634:
	vmovq	%r15, %xmm1
	vpinsrq	$1, %rcx, %xmm1, %xmm0
	testq	%r12, %r12
	je	.L635
	movq	16(%r13), %rsi
	movq	%r12, %rdi
	vmovdqa	%xmm0, (%rsp)
	subq	%r12, %rsi
	call	_ZdlPvm@PLT
	vmovdqa	(%rsp), %xmm0
.L635:
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
.L637:
	.cfi_restore_state
	movabsq	$9223372036854775800, %rbx
.L630:
	movq	%rbx, %rdi
	movq	%rdx, 24(%rsp)
	movq	%rsi, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %r15
	movq	(%rsp), %rsi
	movq	24(%rsp), %rdx
	addq	%rax, %rbx
	leaq	8(%rax), %rcx
	jmp	.L636
.L631:
	movabsq	$1152921504606846975, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	leaq	0(,%rax,8), %rbx
	jmp	.L630
.L645:
	leaq	.LC45(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE6764:
	.size	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, .-_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.section	.text._ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_,"axG",@progbits,_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
	.type	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_, @function
_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_:
.LFB6825:
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
	movabsq	$288230376151711743, %rdx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %r14
	movq	(%rdi), %r13
	movq	%r14, %rax
	subq	%r13, %rax
	sarq	$5, %rax
	cmpq	%rdx, %rax
	je	.L667
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
	jne	.L659
	testq	%rax, %rax
	jne	.L651
	xorl	%ebx, %ebx
	xorl	%edi, %edi
.L657:
	vmovdqu	(%r15), %xmm2
	vmovdqu	16(%r15), %xmm3
	subq	%r12, %r14
	leaq	32(%rdi,%rdx), %r15
	leaq	(%r15,%r14), %rax
	vmovq	%rdi, %xmm1
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqa	%xmm0, (%rsp)
	vmovdqu	%xmm2, (%rdi,%rdx)
	vmovdqu	%xmm3, 16(%rdi,%rdx)
	testq	%rdx, %rdx
	jg	.L668
	testq	%r14, %r14
	jg	.L655
	testq	%r13, %r13
	jne	.L666
.L656:
	vmovdqa	(%rsp), %xmm4
	movq	%rbx, 16(%rbp)
	vmovdqu	%xmm4, 0(%rbp)
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
.L668:
	.cfi_restore_state
	movq	%r13, %rsi
	call	memmove@PLT
	testq	%r14, %r14
	jg	.L655
.L666:
	movq	16(%rbp), %rsi
	movq	%r13, %rdi
	subq	%r13, %rsi
	call	_ZdlPvm@PLT
	jmp	.L656
	.p2align 4
	.p2align 3
.L655:
	movq	%r14, %rdx
	movq	%r12, %rsi
	movq	%r15, %rdi
	call	memcpy@PLT
	testq	%r13, %r13
	je	.L656
	jmp	.L666
	.p2align 4
	.p2align 3
.L659:
	movabsq	$9223372036854775776, %rbx
.L650:
	movq	%rbx, %rdi
	movq	%rdx, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rdx
	addq	%rax, %rbx
	jmp	.L657
	.p2align 4
	.p2align 3
.L651:
	movabsq	$288230376151711743, %rbx
	cmpq	%rbx, %rax
	cmovbe	%rax, %rbx
	salq	$5, %rbx
	jmp	.L650
.L667:
	leaq	.LC45(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE6825:
	.size	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_, .-_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
	.section	.text._ZNSt6vectorImSaImEE17_M_realloc_insertIJRKmEEEvN9__gnu_cxx17__normal_iteratorIPmS1_EEDpOT_,"axG",@progbits,_ZNSt6vectorImSaImEE17_M_realloc_insertIJRKmEEEvN9__gnu_cxx17__normal_iteratorIPmS1_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorImSaImEE17_M_realloc_insertIJRKmEEEvN9__gnu_cxx17__normal_iteratorIPmS1_EEDpOT_
	.type	_ZNSt6vectorImSaImEE17_M_realloc_insertIJRKmEEEvN9__gnu_cxx17__normal_iteratorIPmS1_EEDpOT_, @function
_ZNSt6vectorImSaImEE17_M_realloc_insertIJRKmEEEvN9__gnu_cxx17__normal_iteratorIPmS1_EEDpOT_:
.LFB6844:
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
	movabsq	$1152921504606846975, %rdx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %r12
	movq	(%rdi), %r14
	movq	%r12, %rax
	subq	%r14, %rax
	sarq	$3, %rax
	cmpq	%rdx, %rax
	je	.L690
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
	jne	.L682
	testq	%rax, %rax
	jne	.L674
	xorl	%ebx, %ebx
	xorl	%edi, %edi
.L680:
	movq	(%r15), %rax
	subq	%r13, %r12
	leaq	8(%rdi,%rdx), %r15
	vmovq	%rdi, %xmm1
	movq	%rax, (%rdi,%rdx)
	leaq	(%r15,%r12), %rax
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqa	%xmm0, (%rsp)
	testq	%rdx, %rdx
	jg	.L691
	testq	%r12, %r12
	jg	.L678
	testq	%r14, %r14
	jne	.L689
.L679:
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
.L691:
	.cfi_restore_state
	movq	%r14, %rsi
	call	memmove@PLT
	testq	%r12, %r12
	jg	.L678
.L689:
	movq	16(%rbp), %rsi
	movq	%r14, %rdi
	subq	%r14, %rsi
	call	_ZdlPvm@PLT
	jmp	.L679
	.p2align 4
	.p2align 3
.L678:
	movq	%r12, %rdx
	movq	%r13, %rsi
	movq	%r15, %rdi
	call	memcpy@PLT
	testq	%r14, %r14
	je	.L679
	jmp	.L689
	.p2align 4
	.p2align 3
.L682:
	movabsq	$9223372036854775800, %rbx
.L673:
	movq	%rbx, %rdi
	movq	%rdx, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rdx
	addq	%rax, %rbx
	jmp	.L680
	.p2align 4
	.p2align 3
.L674:
	movabsq	$1152921504606846975, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	leaq	0(,%rax,8), %rbx
	jmp	.L673
.L690:
	leaq	.LC45(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE6844:
	.size	_ZNSt6vectorImSaImEE17_M_realloc_insertIJRKmEEEvN9__gnu_cxx17__normal_iteratorIPmS1_EEDpOT_, .-_ZNSt6vectorImSaImEE17_M_realloc_insertIJRKmEEEvN9__gnu_cxx17__normal_iteratorIPmS1_EEDpOT_
	.section	.text._ZNSt6vectorImSaImEE17_M_default_appendEm,"axG",@progbits,_ZNSt6vectorImSaImEE17_M_default_appendEm,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorImSaImEE17_M_default_appendEm
	.type	_ZNSt6vectorImSaImEE17_M_default_appendEm, @function
_ZNSt6vectorImSaImEE17_M_default_appendEm:
.LFB6848:
	.cfi_startproc
	endbr64
	testq	%rsi, %rsi
	je	.L722
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movabsq	$1152921504606846975, %rcx
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
	sarq	$3, %rax
	sarq	$3, %r13
	subq	%r13, %rcx
	cmpq	%rax, %rsi
	jbe	.L725
	cmpq	%rsi, %rcx
	jb	.L726
	cmpq	%r13, %rsi
	movq	%r13, %rax
	cmovnb	%rsi, %rax
	addq	%r13, %rax
	jc	.L698
	testq	%rax, %rax
	jne	.L727
	movq	%rbp, %r8
	xorl	%r15d, %r15d
	xorl	%ecx, %ecx
.L700:
	movq	%rbx, %rdx
	addq	%rcx, %rbp
	decq	%rdx
	movq	$0, 0(%rbp)
	je	.L704
	leaq	8(%rbp), %rdi
	salq	$3, %rdx
	xorl	%esi, %esi
	movq	%r8, 8(%rsp)
	movq	%rcx, (%rsp)
	call	memset@PLT
	movq	(%rsp), %rcx
	movq	8(%rsp), %r8
.L704:
	testq	%r8, %r8
	jg	.L728
	testq	%r14, %r14
	jne	.L729
.L706:
	addq	%r13, %rbx
	vmovq	%rcx, %xmm1
	movq	%r15, 16(%r12)
	leaq	(%rcx,%rbx,8), %rax
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
.L725:
	.cfi_restore_state
	decq	%rbx
	movq	$0, (%rdx)
	leaq	8(%rdx), %rcx
	je	.L695
	leaq	(%rcx,%rbx,8), %rax
	movq	%rcx, %rdi
	xorl	%esi, %esi
	subq	%rdx, %rax
	leaq	-8(%rax), %rbx
	movq	%rbx, %rdx
	call	memset@PLT
	movq	%rax, %rcx
	addq	%rbx, %rcx
.L695:
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
.L722:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L728:
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
.L705:
	movq	%r14, %rdi
	movq	%rcx, (%rsp)
	call	_ZdlPvm@PLT
	movq	(%rsp), %rcx
	jmp	.L706
	.p2align 4
	.p2align 3
.L729:
	movq	16(%r12), %rsi
	subq	%r14, %rsi
	jmp	.L705
.L727:
	movabsq	$1152921504606846975, %r15
	cmpq	%r15, %rax
	cmovbe	%rax, %r15
	salq	$3, %r15
.L699:
	movq	%r15, %rdi
	call	_Znwm@PLT
	movq	(%r12), %r14
	movq	8(%r12), %r8
	movq	%rax, %rcx
	addq	%rax, %r15
	subq	%r14, %r8
	jmp	.L700
.L698:
	movabsq	$9223372036854775800, %r15
	jmp	.L699
.L726:
	leaq	.LC34(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE6848:
	.size	_ZNSt6vectorImSaImEE17_M_default_appendEm, .-_ZNSt6vectorImSaImEE17_M_default_appendEm
	.section	.text._ZN7FastMapC2ERK7Circuit,"axG",@progbits,_ZN7FastMapC5ERK7Circuit,comdat
	.align 2
	.p2align 4
	.weak	_ZN7FastMapC2ERK7Circuit
	.type	_ZN7FastMapC2ERK7Circuit, @function
_ZN7FastMapC2ERK7Circuit:
.LFB5766:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5766
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movl	$320, %edx
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
	movq	%rsi, %r12
	movq	%rdi, %rbx
	subq	$56, %rsp
	xorl	%esi, %esi
	call	memset@PLT
	leaq	320(%rbx), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movl	$57600, %edx
	movq	%rax, 24(%rsp)
	leaq	344(%rbx), %rax
	vmovdqu64	%zmm0, 320(%rbx)
	xorl	%esi, %esi
	movq	%rax, 16(%rsp)
	leaq	416(%rbx), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movq	%rax, %rdi
	vmovdqu	%ymm0, 384(%rbx)
	movq	%rax, (%rsp)
	vzeroupper
	call	memset@PLT
	xorl	%eax, %eax
	movl	$1, %ecx
	movl	nq(%rip), %r11d
	leal	(%r11,%r11), %edx
	movslq	%edx, %rsi
	testl	%edx, %edx
	jle	.L735
	.p2align 4
	.p2align 3
.L734:
	shlx	%rax, %rcx, %rdx
	movq	%rdx, (%rbx,%rax,8)
	incq	%rax
	cmpq	%rax, %rsi
	jne	.L734
.L735:
	movq	8(%r12), %rdi
	movq	(%r12), %rax
	movq	%rdi, 8(%rsp)
	cmpq	%rax, %rdi
	je	.L794
	movq	%rax, 32(%rsp)
	xorl	%r8d, %r8d
	.p2align 4
	.p2align 3
.L733:
	testl	%r11d, %r11d
	jle	.L738
	movq	32(%rsp), %r12
	movl	%r11d, %r9d
	movq	%rbx, %rcx
	leal	(%r11,%r11), %r10d
	.p2align 4
	.p2align 3
.L737:
	movslq	(%r12), %rdx
	leaq	_ZL5words(%rip), %rax
	movslq	%r9d, %rdi
	salq	$5, %rdx
	addq	%rax, %rdx
	movq	(%rdx), %rax
	movq	8(%rdx), %rsi
	addq	%rax, %rsi
	cmpq	%rsi, %rax
	jne	.L741
	jmp	.L742
	.p2align 4
	.p2align 3
.L739:
	cmpb	$83, %dl
	jne	.L740
	movq	(%rbx,%rdi,8), %rdx
	xorq	%rdx, (%rcx)
.L740:
	incq	%rax
	cmpq	%rax, %rsi
	je	.L742
.L741:
	movzbl	(%rax), %edx
	cmpb	$72, %dl
	jne	.L739
	movq	(%rcx), %rdx
	movq	(%rbx,%rdi,8), %r13
	incq	%rax
	movq	%r13, (%rcx)
	movq	%rdx, (%rbx,%rdi,8)
	cmpq	%rax, %rsi
	jne	.L741
.L742:
	incl	%r9d
	addq	$4, %r12
	addq	$8, %rcx
	cmpl	%r10d, %r9d
	jne	.L737
.L738:
	movq	32(%rsp), %rax
	movq	80(%rax), %r14
	movq	88(%rax), %rax
	movq	%rax, 40(%rsp)
	cmpq	%rax, %r14
	jne	.L748
	jmp	.L743
	.p2align 4
	.p2align 3
.L798:
	movq	(%rbx,%r15,8), %rax
	addq	$8, %r8
	movq	%rax, -8(%r8)
	movq	%r8, 328(%rbx)
.L745:
	leal	(%r11,%r13), %eax
	movq	352(%rbx), %rsi
	cltq
	cmpq	360(%rbx), %rsi
	je	.L746
	movq	(%rbx,%rax,8), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 352(%rbx)
.L747:
	addl	%r11d, %r12d
	addq	$8, %r14
	movq	(%rbx,%r15,8), %rdx
	movslq	%r12d, %r12
	xorq	%rdx, (%rbx,%r13,8)
	movq	(%rbx,%rax,8), %rax
	movq	328(%rbx), %r8
	xorq	%rax, (%rbx,%r12,8)
	cmpq	%r14, 40(%rsp)
	je	.L743
.L748:
	movslq	4(%r14), %r15
	movslq	(%r14), %r13
	movq	%r15, %r12
	cmpq	%r8, 336(%rbx)
	jne	.L798
	movq	24(%rsp), %rdi
	leaq	(%rbx,%r15,8), %rdx
	movq	%r8, %rsi
.LEHB25:
	call	_ZNSt6vectorImSaImEE17_M_realloc_insertIJRKmEEEvN9__gnu_cxx17__normal_iteratorIPmS1_EEDpOT_
	movl	nq(%rip), %r11d
	jmp	.L745
	.p2align 4
	.p2align 3
.L746:
	movq	16(%rsp), %rdi
	leaq	(%rbx,%rax,8), %rdx
	call	_ZNSt6vectorImSaImEE17_M_realloc_insertIJRKmEEEvN9__gnu_cxx17__normal_iteratorIPmS1_EEDpOT_
	movl	nq(%rip), %r11d
	leal	0(%r13,%r11), %eax
	cltq
	jmp	.L747
	.p2align 4
	.p2align 3
.L743:
	addq	$104, 32(%rsp)
	movq	32(%rsp), %rax
	cmpq	%rax, 8(%rsp)
	jne	.L733
	movq	320(%rbx), %r14
	movq	%r8, %rcx
	movq	376(%rbx), %r10
	movq	368(%rbx), %rax
	subq	%r14, %rcx
	movq	%rcx, %rdx
	movq	%r10, %rdi
	sarq	$3, %rdx
	subq	%rax, %rdi
	movq	%rdx, %r9
	movq	%rdx, %rsi
	cmpq	%rdi, %rcx
	ja	.L799
	jnb	.L797
	addq	%rcx, %rax
	cmpq	%rax, %r10
	je	.L797
	movq	%rax, 376(%rbx)
.L797:
	movq	400(%rbx), %rdi
	movq	392(%rbx), %rdx
	movq	%rdi, %rax
	subq	%rdx, %rax
	movq	%rax, %r10
	sarq	$3, %r10
	cmpq	%rax, %rcx
	ja	.L800
	jnb	.L757
	addq	%rcx, %rdx
	cmpq	%rdi, %rdx
	je	.L757
	movq	%rdx, 400(%rbx)
.L757:
	testl	%r9d, %r9d
	jle	.L794
	movl	nq(%rip), %edx
	movq	(%rsp), %r12
	xorl	%r13d, %r13d
	movq	$1, 40(%rsp)
	movq	%r14, %r15
	vmovq	%r8, %xmm1
	leal	(%rdx,%rdx), %eax
	vmovd	%eax, %xmm0
	cltq
	movq	%rax, 32(%rsp)
	.p2align 4
	.p2align 3
.L760:
	vmovd	%xmm0, %eax
	testl	%eax, %eax
	jle	.L762
	movq	344(%rbx), %r9
	movq	368(%rbx), %rcx
	leaq	(%r15,%r13), %rsi
	vmovq	%r12, %xmm2
	movq	392(%rbx), %r14
	movq	32(%rsp), %r10
	xorl	%edi, %edi
	movq	%rsi, %r8
	addq	%r13, %r9
	addq	%r13, %rcx
	movq	%r9, %r12
	addq	%r13, %r14
	movq	%rcx, %r9
	.p2align 4
	.p2align 3
.L758:
	movq	(%r12), %r11
	movq	(%rbx,%rdi,8), %rcx
	shrx	%rdx, %r11, %rax
	shrx	%rdx, %rcx, %rsi
	andq	%rsi, %r11
	andq	%rcx, %rax
	xorq	%r11, %rax
	popcntq	%rax, %rax
	andl	$1, %eax
	shlx	%rdi, %rax, %rax
	orq	%rax, (%r9)
	movq	(%r8), %r11
	shrx	%rdx, %r11, %rax
	andq	%rsi, %r11
	andq	%rcx, %rax
	xorq	%r11, %rax
	popcntq	%rax, %rax
	andl	$1, %eax
	shlx	%rdi, %rax, %rax
	incq	%rdi
	orq	%rax, (%r14)
	cmpq	%r10, %rdi
	jne	.L758
	vmovq	%xmm2, %r12
.L762:
	movq	40(%rsp), %r9
	vmovq	%xmm1, %r8
	subq	%r15, %r8
	sarq	$3, %r8
	cmpl	%r9d, %r8d
	jle	.L794
	.p2align 4
	.p2align 3
.L759:
	movq	344(%rbx), %rax
	leaq	0(,%r9,8), %r11
	movq	(%r15,%r11), %rcx
	movq	(%rax,%r13), %r8
	movq	(%rax,%r11), %rax
	movq	%rcx, %rdi
	shrx	%rdx, %rcx, %r10
	shrx	%rdx, %r8, %rsi
	shrx	%rdx, %rax, %r11
	movq	%r8, %r14
	andq	%rsi, %rdi
	andq	%r11, %r8
	andq	%rax, %rsi
	andq	%r10, %r14
	xorq	%r8, %rsi
	movq	(%r15,%r13), %r8
	xorq	%r14, %rdi
	popcntq	%rdi, %rdi
	popcntq	%rsi, %rsi
	andl	$1, %edi
	andl	$1, %esi
	movb	%dil, (%r12,%r9,4)
	movb	%sil, 1(%r12,%r9,4)
	shrx	%rdx, %r8, %r14
	andq	%r8, %r10
	andq	%r11, %r8
	andq	%r14, %rcx
	andq	%r14, %rax
	xorq	%r8, %rax
	xorq	%r10, %rcx
	popcntq	%rcx, %rcx
	popcntq	%rax, %rax
	andl	$1, %eax
	andl	$1, %ecx
	movb	%al, 3(%r12,%r9,4)
	movb	%cl, 2(%r12,%r9,4)
	movq	328(%rbx), %r8
	movq	320(%rbx), %r15
	incq	%r9
	movq	%r8, %rax
	subq	%r15, %rax
	sarq	$3, %rax
	movl	%eax, %edi
	cmpl	%r9d, %eax
	jg	.L759
	incq	40(%rsp)
	vmovq	%r8, %xmm1
	addq	$8, %r13
	addq	$480, %r12
	movq	40(%rsp), %rax
	decl	%eax
	cmpl	%eax, %edi
	jg	.L760
.L794:
	addq	$56, %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
.L800:
	.cfi_restore_state
	subq	%r10, %rsi
	leaq	392(%rbx), %rdi
	call	_ZNSt6vectorImSaImEE17_M_default_appendEm
	movq	328(%rbx), %r8
	movq	320(%rbx), %r14
	movq	%r8, %r9
	subq	%r14, %r9
	sarq	$3, %r9
	jmp	.L757
.L799:
	sarq	$3, %rdi
	subq	%rdi, %rsi
	leaq	368(%rbx), %rdi
	call	_ZNSt6vectorImSaImEE17_M_default_appendEm
.LEHE25:
	movq	328(%rbx), %r8
	movq	320(%rbx), %r14
	movq	%r8, %rcx
	subq	%r14, %rcx
	movq	%rcx, %r9
	sarq	$3, %r9
	movq	%r9, %rsi
	jmp	.L797
.L768:
	endbr64
	movq	%rax, %r12
.L763:
	movq	392(%rbx), %rdi
	movq	408(%rbx), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L793
	vzeroupper
	call	_ZdlPvm@PLT
.L764:
	movq	368(%rbx), %rdi
	movq	384(%rbx), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L765
	call	_ZdlPvm@PLT
.L765:
	movq	344(%rbx), %rdi
	movq	360(%rbx), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L766
	call	_ZdlPvm@PLT
.L766:
	movq	320(%rbx), %rdi
	movq	336(%rbx), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L767
	call	_ZdlPvm@PLT
.L767:
	movq	%r12, %rdi
.LEHB26:
	call	_Unwind_Resume@PLT
.LEHE26:
.L793:
	vzeroupper
	jmp	.L764
	.cfi_endproc
.LFE5766:
	.section	.gcc_except_table
.LLSDA5766:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE5766-.LLSDACSB5766
.LLSDACSB5766:
	.uleb128 .LEHB25-.LFB5766
	.uleb128 .LEHE25-.LEHB25
	.uleb128 .L768-.LFB5766
	.uleb128 0
	.uleb128 .LEHB26-.LFB5766
	.uleb128 .LEHE26-.LEHB26
	.uleb128 0
	.uleb128 0
.LLSDACSE5766:
	.section	.text._ZN7FastMapC2ERK7Circuit,"axG",@progbits,_ZN7FastMapC5ERK7Circuit,comdat
	.size	_ZN7FastMapC2ERK7Circuit, .-_ZN7FastMapC2ERK7Circuit
	.weak	_ZN7FastMapC1ERK7Circuit
	.set	_ZN7FastMapC1ERK7Circuit,_ZN7FastMapC2ERK7Circuit
	.section	.text._ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,"axG",@progbits,_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.type	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, @function
_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_:
.LFB6977:
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
	movabsq	$1152921504606846975, %rcx
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
	sarq	$3, %rax
	cmpq	%rcx, %rax
	je	.L820
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
	jne	.L812
	testq	%rax, %rax
	jne	.L806
	movl	$8, %ecx
	xorl	%ebx, %ebx
	xorl	%r15d, %r15d
.L811:
	movq	(%rdx), %rax
	movq	%rax, (%r15,%rsi)
	cmpq	%r12, %rbp
	je	.L807
	movq	%rbp, %rsi
	movq	%r15, %rdx
	movq	%r12, %rax
	subq	%r12, %rsi
	.p2align 4
	.p2align 3
.L808:
	movq	(%rax), %rcx
	addq	$8, %rax
	addq	$8, %rdx
	movq	%rcx, -8(%rdx)
	cmpq	%rbp, %rax
	jne	.L808
	leaq	8(%r15,%rsi), %rcx
.L807:
	cmpq	%r14, %rbp
	je	.L809
	subq	%rbp, %r14
	movq	%rcx, %rdi
	movq	%rbp, %rsi
	movq	%r14, %rdx
	call	memcpy@PLT
	movq	%rax, %rcx
	addq	%r14, %rcx
.L809:
	vmovq	%r15, %xmm1
	vpinsrq	$1, %rcx, %xmm1, %xmm0
	testq	%r12, %r12
	je	.L810
	movq	16(%r13), %rsi
	movq	%r12, %rdi
	vmovdqa	%xmm0, (%rsp)
	subq	%r12, %rsi
	call	_ZdlPvm@PLT
	vmovdqa	(%rsp), %xmm0
.L810:
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
.L812:
	.cfi_restore_state
	movabsq	$9223372036854775800, %rbx
.L805:
	movq	%rbx, %rdi
	movq	%rdx, 24(%rsp)
	movq	%rsi, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %r15
	movq	(%rsp), %rsi
	movq	24(%rsp), %rdx
	addq	%rax, %rbx
	leaq	8(%rax), %rcx
	jmp	.L811
.L806:
	movabsq	$1152921504606846975, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	leaq	0(,%rax,8), %rbx
	jmp	.L805
.L820:
	leaq	.LC45(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE6977:
	.size	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, .-_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.section	.text.unlikely
.LCOLDB46:
	.text
.LHOTB46:
	.p2align 4
	.globl	_Z8matchingv
	.type	_Z8matchingv, @function
_Z8matchingv:
.LFB5646:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5646
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
	subq	$56, %rsp
	.cfi_def_cfa_offset 112
	movq	8+edges(%rip), %rdx
	movq	edges(%rip), %rcx
	movq	%fs:40, %rax
	movq	%rax, 40(%rsp)
	xorl	%eax, %eax
	movq	%rdx, %rdi
	subq	%rcx, %rdi
	movq	%rdi, 8(%rsp)
	je	.L840
	movabsq	$9223372036854775800, %rax
	cmpq	%rax, %rdi
	ja	.L852
.LEHB27:
	call	_Znwm@PLT
.LEHE27:
	movq	8+edges(%rip), %rdx
	movq	edges(%rip), %rcx
	movq	%rax, %r12
	cmpq	%rdx, %rcx
	je	.L825
.L855:
	subq	%rcx, %rdx
	xorl	%ebx, %ebx
	.p2align 4
	.p2align 3
.L826:
	movq	(%rcx,%rbx), %rax
	movq	%rax, (%r12,%rbx)
	addq	$8, %rbx
	cmpq	%rdx, %rbx
	jne	.L826
	addq	%r12, %rbx
	leaq	rng(%rip), %rdx
	movq	%r12, %rdi
	movq	%rbx, %rsi
	call	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 16(%r13)
	vmovdqu	%xmm0, 0(%r13)
	cmpq	%rbx, %r12
	je	.L828
	movq	%r12, %rbp
	xorl	%r14d, %r14d
	movl	$1, %r15d
	jmp	.L834
	.p2align 4
	.p2align 3
.L829:
	addq	$8, %rbp
	cmpq	%rbp, %rbx
	je	.L828
.L834:
	vmovq	0(%rbp), %xmm0
	vpextrd	$1, %xmm0, %eax
	vmovd	%xmm0, %edx
	vpshufd	$225, %xmm0, %xmm1
	shlx	%rax, %r15, %rax
	btsq	%rdx, %rax
	testq	%r14, %rax
	jne	.L829
	orq	%rax, %r14
	movq	2496+rng(%rip), %rax
	cmpq	$311, %rax
	ja	.L853
.L830:
	leaq	rng(%rip), %rdi
	leaq	1(%rax), %rdx
	movabsq	$8202884508482404352, %rcx
	movabsq	$-2270628950310912, %rsi
	movq	(%rdi,%rax,8), %rax
	movq	%rdx, 2496+rng(%rip)
	movabsq	$6148914691236517205, %rdi
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%rdi, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rcx, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rsi, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	testb	$1, %al
	je	.L831
	vmovdqa	%xmm1, %xmm0
.L831:
	movq	8(%r13), %rsi
	vmovq	%xmm0, 32(%rsp)
	cmpq	16(%r13), %rsi
	je	.L832
	movq	32(%rsp), %rax
	addq	$8, %rsi
	addq	$8, %rbp
	movq	%rax, -8(%rsi)
	movq	%rsi, 8(%r13)
	cmpq	%rbp, %rbx
	jne	.L834
.L828:
	movq	%r12, %rdi
	movq	8(%rsp), %rsi
	call	_ZdlPvm@PLT
.L821:
	movq	40(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L854
	addq	$56, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	movq	%r13, %rax
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
.L853:
	.cfi_restore_state
	leaq	rng(%rip), %rdi
	vmovq	%xmm0, 24(%rsp)
	vmovq	%xmm1, 16(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	vmovq	24(%rsp), %xmm0
	vmovq	16(%rsp), %xmm1
	movq	2496+rng(%rip), %rax
	jmp	.L830
	.p2align 4
	.p2align 3
.L840:
	xorl	%r12d, %r12d
	cmpq	%rdx, %rcx
	jne	.L855
.L825:
	leaq	rng(%rip), %rdx
	movq	%r12, %rsi
	movq	%r12, %rdi
	call	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 16(%r13)
	vmovdqu	%xmm0, 0(%r13)
	testq	%r12, %r12
	je	.L821
	jmp	.L828
	.p2align 4
	.p2align 3
.L832:
	leaq	32(%rsp), %rdx
	movq	%r13, %rdi
.LEHB28:
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
.LEHE28:
	jmp	.L829
.L852:
	testq	%rdi, %rdi
	jns	.L824
.LEHB29:
	call	_ZSt28__throw_bad_array_new_lengthv@PLT
.L824:
	call	_ZSt17__throw_bad_allocv@PLT
.LEHE29:
.L854:
	call	__stack_chk_fail@PLT
.L841:
	endbr64
	movq	%rax, %rbp
	jmp	.L836
	.section	.gcc_except_table
.LLSDA5646:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE5646-.LLSDACSB5646
.LLSDACSB5646:
	.uleb128 .LEHB27-.LFB5646
	.uleb128 .LEHE27-.LEHB27
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB28-.LFB5646
	.uleb128 .LEHE28-.LEHB28
	.uleb128 .L841-.LFB5646
	.uleb128 0
	.uleb128 .LEHB29-.LFB5646
	.uleb128 .LEHE29-.LEHB29
	.uleb128 0
	.uleb128 0
.LLSDACSE5646:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC5646
	.type	_Z8matchingv.cold, @function
_Z8matchingv.cold:
.LFSB5646:
.L836:
	.cfi_def_cfa_offset 112
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	movq	0(%r13), %rdi
	movq	16(%r13), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L850
	vzeroupper
	call	_ZdlPvm@PLT
.L837:
	movq	8(%rsp), %rsi
	movq	%r12, %rdi
	call	_ZdlPvm@PLT
	movq	%rbp, %rdi
.LEHB30:
	call	_Unwind_Resume@PLT
.LEHE30:
.L850:
	vzeroupper
	jmp	.L837
	.cfi_endproc
.LFE5646:
	.section	.gcc_except_table
.LLSDAC5646:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSEC5646-.LLSDACSBC5646
.LLSDACSBC5646:
	.uleb128 .LEHB30-.LCOLDB46
	.uleb128 .LEHE30-.LEHB30
	.uleb128 0
	.uleb128 0
.LLSDACSEC5646:
	.section	.text.unlikely
	.text
	.size	_Z8matchingv, .-_Z8matchingv
	.section	.text.unlikely
	.size	_Z8matchingv.cold, .-_Z8matchingv.cold
.LCOLDE46:
	.text
.LHOTE46:
	.section	.text.unlikely
.LCOLDB58:
	.text
.LHOTB58:
	.p2align 4
	.globl	_Z6mutateR7Circuit
	.type	_Z6mutateR7Circuit, @function
_Z6mutateR7Circuit:
.LFB5705:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5705
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
	movq	%rdi, %r13
	leaq	rng(%rip), %r12
	andq	$-64, %rsp
	subq	$192, %rsp
	movq	%fs:40, %rax
	movq	%rax, 184(%rsp)
	xorl	%eax, %eax
	movq	2496+rng(%rip), %rax
	cmpq	$311, %rax
	ja	.L1061
.L857:
	movq	(%r12,%rax,8), %rcx
	leaq	1(%rax), %rsi
	movabsq	$6148914691236517205, %rdx
	movabsq	$2951479051793528259, %rdi
	movslq	rounds(%rip), %rbx
	movq	%rsi, 2496+rng(%rip)
	movq	%rcx, %rax
	shrq	$29, %rax
	andq	%rdx, %rax
	movabsq	$8202884508482404352, %rdx
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$17, %rax
	andq	%rdx, %rax
	movabsq	$-2270628950310912, %rdx
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$37, %rax
	andq	%rdx, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	shrq	$43, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rdx
	shrq	$2, %rdx
	movq	%rdx, %rax
	mulq	%rdi
	shrq	$2, %rdx
	imulq	$100, %rdx, %rdx
	subq	%rdx, %rcx
	cmpq	$44, %rcx
	ja	.L858
	cmpq	$311, %rsi
	ja	.L1062
.L859:
	movq	2496+rng(%rip), %rax
	movabsq	$6148914691236517205, %rsi
	leaq	1(%rax), %rcx
	movq	(%r12,%rax,8), %rax
	movq	%rcx, 2496+rng(%rip)
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%rsi, %rdx
	movabsq	$8202884508482404352, %rsi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rsi, %rdx
	movabsq	$-2270628950310912, %rsi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rsi, %rdx
	movq	0(%r13), %rsi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	xorl	%edx, %edx
	movq	%rsi, 24(%rsp)
	divq	%rbx
	movslq	%edx, %rax
	movq	%rdx, %r15
	imulq	$104, %rax, %rax
	addq	%rsi, %rax
	movq	%rax, %rbx
	movq	%rax, 72(%rsp)
	movq	88(%rax), %rax
	movq	80(%rbx), %rbx
	cmpq	%rax, %rbx
	je	.L856
	subq	%rbx, %rax
	sarq	$3, %rax
	movq	%rax, %r13
	cmpq	$311, %rcx
	ja	.L1063
.L862:
	movq	(%r12,%rcx,8), %rax
	leaq	1(%rcx), %rsi
	movabsq	$6148914691236517205, %rcx
	movslq	%r13d, %r13
	movq	%rsi, 2496+rng(%rip)
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
	xorl	%edx, %edx
	divq	%r13
	movslq	%edx, %rdx
	vmovq	(%rbx,%rdx,8), %xmm0
	vmovd	%xmm0, 48(%rsp)
	vpshufd	$225, %xmm0, %xmm1
	vmovq	%xmm0, 176(%rsp)
	cmpq	$311, %rsi
	ja	.L1064
.L863:
	movq	(%r12,%rsi,8), %rax
	leaq	1(%rsi), %rdx
	movabsq	$6148914691236517205, %rsi
	movq	%rdx, 2496+rng(%rip)
	movq	%rax, %rcx
	shrq	$29, %rcx
	andq	%rsi, %rcx
	movabsq	$8202884508482404352, %rsi
	xorq	%rcx, %rax
	movq	%rax, %rcx
	salq	$17, %rcx
	andq	%rsi, %rcx
	movabsq	$-2270628950310912, %rsi
	xorq	%rcx, %rax
	movq	%rax, %rcx
	salq	$37, %rcx
	andq	%rsi, %rcx
	xorq	%rcx, %rax
	movq	%rax, %rcx
	shrq	$43, %rcx
	xorq	%rcx, %rax
	testb	$1, %al
	je	.L864
	vmovq	%xmm1, 176(%rsp)
.L864:
	cmpq	$311, %rdx
	ja	.L1065
.L865:
	movq	(%r12,%rdx,8), %rax
	leaq	1(%rdx), %r8
	movabsq	$6148914691236517205, %r14
	movabsq	$8202884508482404352, %r13
	movabsq	$-2270628950310912, %rbx
	movq	%r8, 2496+rng(%rip)
	movq	$0, 88(%rsp)
	vmovq	%r8, %xmm7
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%r14, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%r13, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rbx, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	testb	$3, %al
	sete	%al
	movzbl	%al, %eax
	incl	%eax
	movl	%eax, 56(%rsp)
	leal	1(%r15), %eax
	movl	%eax, 64(%rsp)
	cltq
	imulq	$104, %rax, %rax
	movq	%rax, 16(%rsp)
	leaq	176(%rsp), %rax
	movq	%rax, 40(%rsp)
.L871:
	movq	40(%rsp), %rax
	vmovq	%xmm7, %r8
	movq	88(%rsp), %rsi
	movl	(%rax,%rsi,4), %eax
	cmpl	48(%rsp), %eax
	movl	%eax, 80(%rsp)
	setne	%al
	movzbl	%al, %eax
	leal	2(%rax,%rax,2), %r15d
	jmp	.L868
	.p2align 4
	.p2align 3
.L867:
	movq	(%r12,%rax,8), %rcx
	leaq	1(%rax), %r8
	movq	%r8, 2496+rng(%rip)
	movq	%rcx, %rax
	shrq	$29, %rax
	andq	%r14, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$17, %rax
	andq	%r13, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$37, %rax
	andq	%rbx, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	shrq	$43, %rax
	xorq	%rax, %rcx
	movabsq	$-3689348814741910323, %rax
	mulq	%rcx
	movq	%rdx, %rax
	andq	$-4, %rdx
	shrq	$2, %rax
	addq	%rax, %rdx
	subq	%rdx, %rcx
	incl	%ecx
	cmpl	%ecx, %r15d
	jne	.L1066
.L868:
	movq	%r8, %rax
	cmpq	$311, %r8
	jbe	.L867
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rax
	jmp	.L867
	.p2align 4
	.p2align 3
.L1066:
	movl	%ecx, %edi
	vmovq	%r8, %xmm7
	movl	$4, %r9d
	cmpl	$3, %ecx
	je	.L869
	cmpl	$4, %ecx
	movl	$3, %r9d
	cmovne	%ecx, %r9d
.L869:
	movslq	80(%rsp), %r15
	movq	72(%rsp), %rax
	movl	%r9d, 36(%rsp)
	salq	$2, %r15
	leaq	(%rax,%r15), %rdx
	movl	(%rdx), %esi
	movq	%rdx, 80(%rsp)
	call	_Z12localcomposeii
	movq	80(%rsp), %rdx
	movl	%eax, (%rdx)
	movl	64(%rsp), %eax
	cmpl	rounds(%rip), %eax
	jge	.L870
	addq	16(%rsp), %r15
	movl	36(%rsp), %esi
	addq	24(%rsp), %r15
	movl	(%r15), %edi
	call	_Z12localcomposeii
	movl	%eax, (%r15)
.L870:
	incq	88(%rsp)
	movq	88(%rsp), %rax
	cmpl	%eax, 56(%rsp)
	jg	.L871
.L856:
	movq	184(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1060
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
.L858:
	.cfi_restore_state
	cmpq	$311, %rsi
	ja	.L1067
.L873:
	movq	(%r12,%rsi,8), %rcx
	movabsq	$6148914691236517205, %rdx
	leaq	1(%rsi), %rdi
	movq	%rdi, 2496+rng(%rip)
	movq	%rcx, %rax
	shrq	$29, %rax
	andq	%rdx, %rax
	movabsq	$8202884508482404352, %rdx
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$17, %rax
	andq	%rdx, %rax
	movabsq	$-2270628950310912, %rdx
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$37, %rax
	andq	%rdx, %rax
	movabsq	$2951479051793528259, %rdx
	xorq	%rax, %rcx
	movq	%rcx, %rax
	shrq	$43, %rax
	xorq	%rax, %rcx
	movq	%rcx, %r14
	shrq	$2, %r14
	movq	%r14, %rax
	mulq	%rdx
	movq	%rdx, %r14
	shrq	$2, %r14
	imulq	$100, %r14, %rax
	subq	%rax, %rcx
	movq	%rcx, %r14
	cmpq	$311, %rdi
	ja	.L1068
.L874:
	movq	(%r12,%rdi,8), %rax
	movabsq	$6148914691236517205, %rsi
	movq	0(%r13), %r15
	leaq	1(%rdi), %rcx
	movq	%rcx, 2496+rng(%rip)
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%rsi, %rdx
	movabsq	$8202884508482404352, %rsi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rsi, %rdx
	movabsq	$-2270628950310912, %rsi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rsi, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	%rbx
	movslq	%edx, %rbx
	imulq	$104, %rbx, %rbx
	addq	%r15, %rbx
	cmpq	$69, %r14
	jbe	.L1069
	cmpq	$77, %r14
	ja	.L878
	movq	88(%rbx), %rax
	movq	80(%rbx), %rbx
	cmpq	%rbx, %rax
	je	.L856
	subq	%rbx, %rax
	sarq	$3, %rax
	movq	%rax, %r13
	cmpq	$311, %rcx
	ja	.L1070
.L880:
	movq	2496+rng(%rip), %rax
	movabsq	$6148914691236517205, %rcx
	movslq	%r13d, %r13
	leaq	1(%rax), %rdx
	movq	(%r12,%rax,8), %rax
	movq	%rdx, 2496+rng(%rip)
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
	xorl	%edx, %edx
	divq	%r13
	movslq	%edx, %rdx
	rolq	$32, (%rbx,%rdx,8)
	jmp	.L856
	.p2align 4
	.p2align 3
.L1061:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rax
	jmp	.L857
	.p2align 4
	.p2align 3
.L878:
	cmpl	$91, %r14d
	jg	.L881
	movq	80(%rbx), %r9
	movq	88(%rbx), %rax
	subq	%r9, %rax
	cmpq	$8, %rax
	ja	.L1071
.L882:
	movq	edges(%rip), %r14
	movq	8+edges(%rip), %rdx
	subq	%r14, %rdx
	sarq	$3, %rdx
	cmpq	$311, %rcx
	ja	.L1072
.L908:
	movq	(%r12,%rcx,8), %rax
	leaq	1(%rcx), %rsi
	movabsq	$6148914691236517205, %rdi
	movq	%rsi, 2496+rng(%rip)
	movq	%rax, %rcx
	shrq	$29, %rcx
	andq	%rdi, %rcx
	movabsq	$8202884508482404352, %rdi
	xorq	%rcx, %rax
	movq	%rax, %rcx
	salq	$17, %rcx
	andq	%rdi, %rcx
	movabsq	$-2270628950310912, %rdi
	xorq	%rcx, %rax
	movq	%rax, %rcx
	salq	$37, %rcx
	andq	%rdi, %rcx
	xorq	%rcx, %rax
	movq	%rax, %rcx
	shrq	$43, %rcx
	xorq	%rcx, %rax
	movslq	%edx, %rcx
	xorl	%edx, %edx
	divq	%rcx
	movslq	%edx, %rdx
	movq	(%r14,%rdx,8), %rax
	movq	%rax, 144(%rsp)
	cmpq	$311, %rsi
	ja	.L1073
.L909:
	leaq	1(%rsi), %rax
	movabsq	$6148914691236517205, %rcx
	movq	%rax, 2496+rng(%rip)
	movq	(%r12,%rsi,8), %rax
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
	testb	$1, %al
	jne	.L1074
.L910:
	movq	88(%rbx), %rcx
	movq	80(%rbx), %rsi
	movq	%rcx, %rdx
	subq	%rsi, %rdx
	sarq	$3, %rdx
	testl	%edx, %edx
	jle	.L911
	vmovq	144(%rsp), %xmm1
	leal	-1(%rdx), %eax
	vpextrd	$1, %xmm1, %r8d
	vmovd	%xmm1, %edi
	cmpl	$14, %eax
	jbe	.L985
	vmovdqa32	.LC47(%rip), %zmm2
	vpbroadcastd	.LC56(%rip), %zmm13
	movl	%edx, %r9d
	vpxor	%xmm4, %xmm4, %xmm4
	vmovdqa32	.LC49(%rip), %zmm12
	vmovdqa32	.LC50(%rip), %zmm11
	shrl	$4, %r9d
	vpbroadcastd	%edi, %zmm7
	vpbroadcastd	.LC57(%rip), %zmm10
	decl	%r9d
	vpbroadcastd	%r8d, %zmm6
	movq	%rsi, %rax
	salq	$7, %r9
	vpternlogd	$0xFF, %zmm5, %zmm5, %zmm5
	vmovdqa32	%zmm4, %zmm9
	leaq	128(%rsi,%r9), %r9
	.p2align 4
	.p2align 3
.L913:
	vmovdqu32	(%rax), %zmm3
	vmovdqu32	(%rax), %zmm0
	vmovdqa32	%zmm2, %zmm8
	subq	$-128, %rax
	vpaddd	%zmm13, %zmm2, %zmm2
	vpermt2d	-64(%rax), %zmm11, %zmm0
	vpermt2d	-64(%rax), %zmm12, %zmm3
	vpcmpd	$0, %zmm0, %zmm6, %k0
	vpcmpd	$0, %zmm0, %zmm7, %k2
	vpcmpd	$0, %zmm3, %zmm6, %k1
	korw	%k0, %k1, %k1
	vpcmpd	$0, %zmm3, %zmm7, %k0
	korw	%k2, %k0, %k0
	kmovw	%k1, %r10d
	kmovw	%k0, %r11d
	orl	%r11d, %r10d
	notl	%r10d
	kmovw	%r10d, %k1
	vpblendmd	%zmm9, %zmm10, %zmm0{%k1}
	vpblendmd	%zmm5, %zmm8, %zmm5{%k1}
	vpaddd	%zmm0, %zmm4, %zmm4
	cmpq	%rax, %r9
	jne	.L913
	vextracti32x8	$0x1, %zmm4, %ymm2
	movl	%edx, %eax
	vpaddd	%ymm4, %ymm2, %ymm2
	andl	$-16, %eax
	vextracti128	$0x1, %ymm2, %xmm0
	movl	%eax, %r11d
	vpaddd	%xmm2, %xmm0, %xmm0
	vpsrldq	$8, %xmm0, %xmm2
	vpaddd	%xmm2, %xmm0, %xmm0
	vpsrldq	$4, %xmm0, %xmm2
	vpaddd	%xmm2, %xmm0, %xmm0
	vextracti32x8	$0x1, %zmm5, %ymm2
	vpmaxsd	%ymm5, %ymm2, %ymm2
	vmovd	%xmm0, %r9d
	vextracti128	$0x1, %ymm2, %xmm0
	vpmaxsd	%xmm2, %xmm0, %xmm0
	vpsrldq	$8, %xmm0, %xmm2
	vpmaxsd	%xmm2, %xmm0, %xmm0
	vpsrldq	$4, %xmm0, %xmm2
	vpmaxsd	%xmm2, %xmm0, %xmm0
	vmovd	%xmm0, %r10d
	cmpl	%edx, %eax
	je	.L914
.L912:
	movl	%edx, %r12d
	subl	%eax, %r12d
	leal	-1(%r12), %r14d
	cmpl	$6, %r14d
	jbe	.L915
	leaq	(%rsi,%rax,8), %rax
	vmovdqa	.LC52(%rip), %ymm2
	vmovdqa	.LC53(%rip), %ymm3
	vpbroadcastd	%r8d, %ymm0
	vmovdqu	(%rax), %ymm5
	vmovdqu	32(%rax), %ymm6
	vpbroadcastd	%edi, %ymm4
	vmovdqa	.LC55(%rip), %ymm7
	vpermi2d	%ymm6, %ymm5, %ymm2
	vpermi2d	%ymm6, %ymm5, %ymm3
	vpcmpd	$0, %ymm2, %ymm4, %k0
	vpcmpd	$0, %ymm2, %ymm0, %k2
	vpbroadcastd	%r11d, %ymm2
	vpaddd	.LC54(%rip), %ymm2, %ymm2
	vpcmpd	$0, %ymm3, %ymm4, %k1
	korb	%k0, %k1, %k1
	vpcmpd	$0, %ymm3, %ymm0, %k0
	vpxor	%xmm3, %xmm3, %xmm3
	vpcmpeqd	%ymm0, %ymm0, %ymm0
	korb	%k2, %k0, %k0
	kmovb	%k1, %eax
	kmovb	%k0, %r14d
	orl	%r14d, %eax
	notl	%eax
	kmovb	%eax, %k1
	vpblendmd	%ymm3, %ymm7, %ymm3{%k1}
	vmovdqa32	%ymm0, %ymm2{%k1}
	vmovdqa	%xmm3, %xmm0
	vextracti128	$0x1, %ymm3, %xmm3
	vpaddd	%xmm3, %xmm0, %xmm0
	vpsrldq	$8, %xmm0, %xmm3
	vpaddd	%xmm3, %xmm0, %xmm0
	vpsrldq	$4, %xmm0, %xmm3
	vpaddd	%xmm3, %xmm0, %xmm0
	vmovd	%xmm0, %eax
	vextracti128	$0x1, %ymm2, %xmm0
	vpmaxsd	%xmm2, %xmm0, %xmm0
	addl	%eax, %r9d
	vpsrldq	$8, %xmm0, %xmm2
	vpmaxsd	%xmm2, %xmm0, %xmm0
	vpsrldq	$4, %xmm0, %xmm2
	vpmaxsd	%xmm2, %xmm0, %xmm0
	vmovd	%xmm0, %eax
	cmpl	$-1, %eax
	cmovne	%eax, %r10d
	movl	%r12d, %eax
	andl	$-8, %eax
	addl	%eax, %r11d
	cmpl	%eax, %r12d
	je	.L914
.L915:
	movslq	%r11d, %rax
	salq	$3, %rax
	leaq	(%rsi,%rax), %r12
	movl	(%r12), %r14d
	movl	4(%r12), %r12d
	cmpl	%edi, %r14d
	je	.L917
	cmpl	%edi, %r12d
	je	.L917
	cmpl	%r8d, %r14d
	je	.L917
	cmpl	%r8d, %r12d
	je	.L917
.L918:
	leal	1(%r11), %r14d
	vmovd	%r14d, %xmm5
	cmpl	%r14d, %edx
	jle	.L914
	leaq	8(%rsi,%rax), %r12
	vmovd	(%r12), %xmm0
	movl	4(%r12), %r12d
	cmpl	%edi, %r12d
	je	.L920
	vmovd	%xmm0, %r14d
	cmpl	%edi, %r14d
	je	.L920
	cmpl	%r8d, %r14d
	je	.L920
	cmpl	%r8d, %r12d
	je	.L920
	vmovd	%r10d, %xmm5
.L921:
	leal	2(%r11), %r10d
	cmpl	%edx, %r10d
	jge	.L987
	leaq	16(%rsi,%rax), %r12
	vmovd	(%r12), %xmm0
	movl	4(%r12), %r12d
	vmovd	%xmm0, %r14d
	cmpl	%edi, %r14d
	je	.L923
	cmpl	%edi, %r12d
	je	.L923
	cmpl	%r8d, %r12d
	je	.L923
	cmpl	%r8d, %r14d
	je	.L923
	vmovd	%xmm5, %r10d
.L924:
	leal	3(%r11), %r14d
	vmovd	%r14d, %xmm6
	cmpl	%edx, %r14d
	jge	.L914
	leaq	24(%rsi,%rax), %r12
	vmovd	(%r12), %xmm0
	movl	4(%r12), %r12d
	cmpl	%edi, %r12d
	je	.L926
	vmovd	%xmm0, %r14d
	cmpl	%edi, %r14d
	je	.L926
	cmpl	%r8d, %r12d
	je	.L926
	cmpl	%r8d, %r14d
	je	.L926
	vmovd	%r10d, %xmm6
.L927:
	leal	4(%r11), %r10d
	cmpl	%r10d, %edx
	jle	.L990
	leaq	32(%rsi,%rax), %r12
	vmovd	(%r12), %xmm0
	movl	4(%r12), %r12d
	vmovd	%xmm0, %r14d
	cmpl	%edi, %r14d
	je	.L929
	cmpl	%edi, %r12d
	je	.L929
	cmpl	%r8d, %r14d
	je	.L929
	cmpl	%r8d, %r12d
	je	.L929
	vmovd	%xmm6, %r10d
.L930:
	leal	5(%r11), %r12d
	cmpl	%edx, %r12d
	jge	.L914
	leaq	40(%rsi,%rax), %r14
	vmovd	4(%r14), %xmm5
	vmovd	(%r14), %xmm0
	vmovd	%xmm5, %r14d
	cmpl	%edi, %r14d
	je	.L932
	vmovd	%xmm0, %r14d
	cmpl	%edi, %r14d
	je	.L932
	vmovd	%xmm5, %r14d
	cmpl	%r8d, %r14d
	je	.L932
	vmovd	%xmm0, %r14d
	cmpl	%r14d, %r8d
	je	.L932
	movl	%r10d, %r12d
.L933:
	leal	6(%r11), %r10d
	cmpl	%r10d, %edx
	jle	.L993
	leaq	48(%rsi,%rax), %rax
	movl	(%rax), %r11d
	movl	4(%rax), %eax
	cmpl	%edi, %eax
	je	.L935
	cmpl	%edi, %r11d
	je	.L935
	cmpl	%r8d, %eax
	je	.L935
	cmpl	%r8d, %r11d
	je	.L935
.L993:
	movl	%r12d, %r10d
	.p2align 4
	.p2align 3
.L914:
	cmpl	$1, %r9d
	je	.L1075
	vzeroupper
.L911:
	sarq	$2, %rdx
	testq	%rdx, %rdx
	jle	.L938
	movl	144(%rsp), %eax
	movl	148(%rsp), %r8d
	salq	$5, %rdx
	addq	%rsi, %rdx
	movl	%eax, %edi
.L946:
	movl	(%rsi), %r9d
	movl	4(%rsi), %r10d
	cmpl	%eax, %r9d
	je	.L939
	cmpl	%eax, %r10d
	je	.L939
	cmpl	%r8d, %r10d
	je	.L939
	cmpl	%r8d, %r9d
	je	.L939
	movl	12(%rsi), %r10d
	movl	8(%rsi), %r9d
	cmpl	%r10d, %r8d
	sete	%r11b
	cmpl	%r9d, %r8d
	sete	%r12b
	orb	%r12b, %r11b
	jne	.L999
	cmpl	%r9d, %eax
	sete	%r9b
	cmpl	%r10d, %eax
	sete	%r10b
	orb	%r10b, %r9b
	je	.L940
.L999:
	addq	$8, %rsi
.L939:
	cmpq	%rcx, %rsi
	je	.L951
	leaq	8(%rsi), %rax
	cmpq	%rcx, %rax
	jne	.L957
	jmp	.L978
	.p2align 4
	.p2align 3
.L1076:
	movl	144(%rsp), %edi
.L957:
	movl	(%rax), %edx
	movl	4(%rax), %r8d
	cmpl	%edi, %edx
	je	.L955
	cmpl	%edi, %r8d
	je	.L955
	movl	148(%rsp), %edi
	cmpl	%edi, %edx
	je	.L955
	cmpl	%edi, %r8d
	je	.L955
	movl	%edx, (%rsi)
	movl	4(%rax), %edx
	addq	$8, %rsi
	movl	%edx, -4(%rsi)
	.p2align 4
	.p2align 3
.L955:
	addq	$8, %rax
	cmpq	%rax, %rcx
	jne	.L1076
	cmpq	%rcx, %rsi
	je	.L953
.L978:
	movq	%rsi, 88(%rbx)
.L953:
	movq	8(%r13), %rcx
	xorl	%edx, %edx
	cmpq	%rcx, %r15
	je	.L958
	.p2align 4
	.p2align 3
.L959:
	movq	88(%r15), %rax
	subq	80(%r15), %rax
	addq	$104, %r15
	sarq	$3, %rax
	addl	%eax, %edx
	cmpq	%r15, %rcx
	jne	.L959
.L958:
	cmpl	%edx, budget(%rip)
	jle	.L856
	cmpq	%rsi, 96(%rbx)
	je	.L961
	movq	144(%rsp), %rax
	addq	$8, %rsi
	movq	%rax, -8(%rsi)
	movq	%rsi, 88(%rbx)
	jmp	.L856
	.p2align 4
	.p2align 3
.L1062:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	jmp	.L859
	.p2align 4
	.p2align 3
.L1069:
	cmpq	$311, %rcx
	ja	.L1077
.L876:
	movq	2496+rng(%rip), %rax
	movabsq	$6148914691236517205, %rdx
	movslq	nq(%rip), %r13
	movq	(%r12,%rax,8), %rcx
	leaq	1(%rax), %rsi
	movq	%rsi, 2496+rng(%rip)
	movq	%rcx, %rax
	shrq	$29, %rax
	andq	%rdx, %rax
	movabsq	$8202884508482404352, %rdx
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$17, %rax
	andq	%rdx, %rax
	movabsq	$-2270628950310912, %rdx
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$37, %rax
	andq	%rdx, %rax
	movabsq	$-6148914691236517205, %rdx
	xorq	%rax, %rcx
	movq	%rcx, %rax
	shrq	$43, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	mulq	%rdx
	shrq	$2, %rdx
	leaq	(%rdx,%rdx,2), %rax
	addq	%rax, %rax
	subq	%rax, %rcx
	movq	%rcx, %r14
	cmpq	$311, %rsi
	ja	.L1078
.L877:
	leaq	1(%rsi), %rax
	movq	%rax, 2496+rng(%rip)
	movq	(%r12,%rsi,8), %rax
	movabsq	$6148914691236517205, %rsi
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%rsi, %rdx
	movabsq	$8202884508482404352, %rsi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rsi, %rdx
	movabsq	$-2270628950310912, %rsi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rsi, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	%r13
	movslq	%edx, %rdx
	movl	%r14d, (%rbx,%rdx,4)
	jmp	.L856
	.p2align 4
	.p2align 3
.L1067:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rsi
	jmp	.L873
	.p2align 4
	.p2align 3
.L1068:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rdi
	jmp	.L874
	.p2align 4
	.p2align 3
.L1064:
	movq	%r12, %rdi
	vmovq	%xmm1, 88(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	vmovq	88(%rsp), %xmm1
	movq	2496+rng(%rip), %rsi
	jmp	.L863
	.p2align 4
	.p2align 3
.L1063:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rcx
	jmp	.L862
	.p2align 4
	.p2align 3
.L1065:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rdx
	jmp	.L865
	.p2align 4
	.p2align 3
.L881:
	cmpl	$97, %r14d
	jle	.L882
	leaq	144(%rsp), %rdi
.LEHB31:
	call	_Z8matchingv
.LEHE31:
	vmovdqa	144(%rsp), %xmm5
	vpxor	%xmm0, %xmm0, %xmm0
	movq	80(%rbx), %rdi
	movq	96(%rbx), %rsi
	vmovdqu	%xmm5, 80(%rbx)
	movq	160(%rsp), %rax
	movq	%rax, 96(%rbx)
	vmovdqa	%xmm0, 144(%rsp)
	movq	$0, 160(%rsp)
	testq	%rdi, %rdi
	je	.L963
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	movq	144(%rsp), %rdi
	movq	160(%rsp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L963
	call	_ZdlPvm@PLT
.L963:
	movq	0(%r13), %r14
	movl	budget(%rip), %r15d
	movabsq	$6148914691236517205, %r8
	movabsq	$8202884508482404352, %rsi
	movq	8(%r13), %r13
	.p2align 4
	.p2align 3
.L965:
	cmpq	%r13, %r14
	je	.L996
	movq	%r14, %rdx
	xorl	%ecx, %ecx
	.p2align 4
	.p2align 3
.L970:
	movq	88(%rdx), %rax
	subq	80(%rdx), %rax
	addq	$104, %rdx
	sarq	$3, %rax
	addl	%eax, %ecx
	cmpq	%r13, %rdx
	jne	.L970
.L969:
	cmpl	%r15d, %ecx
	jle	.L856
	movq	88(%rbx), %rcx
	movq	80(%rbx), %r9
	movq	%rcx, %rdx
	subq	%r9, %rdx
	sarq	$3, %rdx
	cmpq	%r9, %rcx
	je	.L856
	movq	2496+rng(%rip), %rax
	cmpq	$311, %rax
	ja	.L1079
.L971:
	leaq	1(%rax), %rdi
	movq	(%r12,%rax,8), %rax
	movabsq	$-2270628950310912, %r11
	movq	%rdi, 2496+rng(%rip)
	movq	%rax, %rdi
	shrq	$29, %rdi
	andq	%r8, %rdi
	xorq	%rdi, %rax
	movq	%rax, %rdi
	salq	$17, %rdi
	andq	%rsi, %rdi
	xorq	%rdi, %rax
	movq	%rax, %rdi
	salq	$37, %rdi
	andq	%r11, %rdi
	xorq	%rdi, %rax
	movq	%rax, %rdi
	shrq	$43, %rdi
	xorq	%rdi, %rax
	movslq	%edx, %rdi
	xorl	%edx, %edx
	divq	%rdi
	movslq	%edx, %rdx
	salq	$3, %rdx
	leaq	8(%r9,%rdx), %rax
	leaq	(%r9,%rdx), %r10
	cmpq	%rcx, %rax
	je	.L968
	movq	%rcx, %r11
	leaq	8(%r9,%rdx), %r9
	subq	%rax, %r11
	xorl	%eax, %eax
	movq	%r11, %rdi
	sarq	$3, %rdi
	salq	$3, %rdi
	testq	%r11, %r11
	jle	.L968
	.p2align 4
	.p2align 3
.L967:
	movq	(%r9,%rax), %rdx
	movq	%rdx, (%r10,%rax)
	addq	$8, %rax
	cmpq	%rax, %rdi
	jne	.L967
.L968:
	subq	$8, %rcx
	movq	%rcx, 88(%rbx)
	jmp	.L965
	.p2align 4
	.p2align 3
.L1079:
	movq	%r12, %rdi
	movq	%rdx, 72(%rsp)
	movq	%r9, 80(%rsp)
	movq	%rcx, 88(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rax
	movabsq	$8202884508482404352, %rsi
	movabsq	$6148914691236517205, %r8
	movq	72(%rsp), %rdx
	movq	80(%rsp), %r9
	movq	88(%rsp), %rcx
	jmp	.L971
	.p2align 4
	.p2align 3
.L996:
	xorl	%ecx, %ecx
	jmp	.L969
.L1078:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rsi
	jmp	.L877
.L1077:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	jmp	.L876
.L1074:
	rolq	$32, 144(%rsp)
	jmp	.L910
.L1075:
	movslq	%r10d, %r10
	vmovq	%xmm1, (%rsi,%r10,8)
	vzeroupper
	jmp	.L856
.L1073:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rsi
	jmp	.L909
.L1072:
	movq	%r12, %rdi
	movq	%rdx, 88(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rcx
	movq	88(%rsp), %rdx
	jmp	.L908
.L917:
	incl	%r9d
	movl	%r11d, %r10d
	jmp	.L918
.L920:
	incl	%r9d
	jmp	.L921
.L923:
	incl	%r9d
	jmp	.L924
.L1070:
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	jmp	.L880
.L926:
	incl	%r9d
	jmp	.L927
.L1071:
	sarq	$3, %rax
	movq	%rax, %r13
	cmpq	$311, %rcx
	ja	.L1080
.L883:
	movq	2496+rng(%rip), %rax
	movabsq	$6148914691236517205, %rsi
	movslq	%r13d, %r15
	leaq	1(%rax), %rcx
	movq	(%r12,%rax,8), %rax
	movq	%rcx, 2496+rng(%rip)
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%rsi, %rdx
	movabsq	$8202884508482404352, %rsi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rsi, %rdx
	movabsq	$-2270628950310912, %rsi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rsi, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	%r15
	movq	%rdx, 56(%rsp)
	movl	%edx, %r14d
	cmpq	$311, %rcx
	ja	.L1081
.L884:
	leaq	1(%rcx), %rax
	movq	%rax, 2496+rng(%rip)
	movq	(%r12,%rcx,8), %rax
	movabsq	$6148914691236517205, %rcx
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
	xorl	%edx, %edx
	divq	%r15
	movq	%rdx, 40(%rsp)
	movl	%edx, %ecx
	cmpl	56(%rsp), %edx
	je	.L856
	xorl	%r15d, %r15d
	testl	%r13d, %r13d
	jle	.L887
	leal	-1(%r13), %esi
	xorl	%eax, %eax
	xorl	%r15d, %r15d
	movl	$1, %r8d
	jmp	.L890
	.p2align 4
	.p2align 3
.L984:
	movq	%rdx, %rax
.L890:
	cmpl	%eax, %ecx
	je	.L889
	cmpl	%eax, %r14d
	je	.L889
	movl	(%r9,%rax,8), %edx
	movl	4(%r9,%rax,8), %edi
	shlx	%rdx, %r8, %rdx
	btsq	%rdi, %rdx
	orq	%rdx, %r15
.L889:
	leaq	1(%rax), %rdx
	cmpq	%rax, %rsi
	jne	.L984
.L887:
	movq	8+edges(%rip), %rax
	movq	edges(%rip), %r13
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 128(%rsp)
	vmovdqa	%xmm0, 112(%rsp)
	movq	%rax, 88(%rsp)
	cmpq	%r13, %rax
	je	.L891
	xorl	%esi, %esi
	xorl	%r14d, %r14d
	jmp	.L894
	.p2align 4
	.p2align 3
.L892:
	addq	$8, %r13
	cmpq	%r13, 88(%rsp)
	je	.L1082
.L894:
	movq	0(%r13), %rax
	movq	%rax, %rdi
	movq	%rax, 144(%rsp)
	shrq	$32, %rdi
	movq	%rdi, %rcx
	movl	$1, %edi
	shlx	%rax, %rdi, %rdx
	btsq	%rcx, %rdx
	testq	%r15, %rdx
	jne	.L892
	cmpq	%rsi, %r14
	je	.L893
	movq	%rax, (%r14)
	addq	$8, %r14
	movq	%r14, 120(%rsp)
	jmp	.L892
.L929:
	incl	%r9d
	jmp	.L930
.L932:
	incl	%r9d
	jmp	.L933
.L1082:
	movq	112(%rsp), %rax
	movq	%r12, %rdx
	subq	%rax, %rsi
	movq	%rax, %rdi
	movq	%rax, 88(%rsp)
	movq	%rsi, 48(%rsp)
	movq	%r14, %rsi
	call	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 160(%rsp)
	movq	88(%rsp), %rax
	vmovdqa	%xmm0, 144(%rsp)
	cmpq	%rax, %r14
	je	.L896
	movq	%rax, %r13
	xorl	%ecx, %ecx
	xorl	%esi, %esi
	jmp	.L903
	.p2align 4
	.p2align 3
.L897:
	addq	$8, %r13
	cmpq	%r13, %r14
	je	.L1083
.L903:
	movq	0(%r13), %rax
	movl	$1, %edi
	vmovq	%rax, %xmm0
	movq	%rax, 104(%rsp)
	shlx	%rax, %rdi, %rax
	vpextrd	$1, %xmm0, %edx
	vpshufd	$225, %xmm0, %xmm1
	btsq	%rdx, %rax
	testq	%r15, %rax
	jne	.L897
	orq	%rax, %r15
	movq	2496+rng(%rip), %rax
	cmpq	$311, %rax
	ja	.L1084
.L898:
	leaq	1(%rax), %rdx
	movq	(%r12,%rax,8), %rax
	movabsq	$6148914691236517205, %rdi
	movq	%rdx, 2496+rng(%rip)
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%rdi, %rdx
	movabsq	$8202884508482404352, %rdi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%rdi, %rdx
	movabsq	$-2270628950310912, %rdi
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rdi, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	testb	$1, %al
	je	.L899
	vmovq	%xmm1, 104(%rsp)
.L899:
	cmpq	%rcx, %rsi
	je	.L900
	movq	104(%rsp), %rax
	addq	$8, %rsi
	movq	%rax, -8(%rsi)
	movq	%rsi, 152(%rsp)
.L901:
	movq	%rsi, %rax
	movq	144(%rsp), %rdi
	subq	%rdi, %rax
	cmpq	$16, %rax
	jne	.L897
	subq	%rdi, %rcx
.L902:
	movq	(%rdi), %rsi
	movq	80(%rbx), %rdx
	movslq	56(%rsp), %rax
	movq	%rsi, (%rdx,%rax,8)
	movslq	40(%rsp), %rax
	movq	8(%rdi), %rsi
	movq	%rsi, (%rdx,%rax,8)
.L905:
	movq	%rcx, %rsi
	call	_ZdlPvm@PLT
.L896:
	cmpq	$0, 88(%rsp)
	je	.L856
	movq	184(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1060
	movq	48(%rsp), %rsi
	movq	88(%rsp), %rdi
	leaq	-40(%rbp), %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	jmp	_ZdlPvm@PLT
.L1084:
	.cfi_restore_state
	movq	%r12, %rdi
	vmovq	%xmm1, 64(%rsp)
	movq	%rcx, 72(%rsp)
	movq	%rsi, 80(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	vmovq	64(%rsp), %xmm1
	movq	2496+rng(%rip), %rax
	movq	72(%rsp), %rcx
	movq	80(%rsp), %rsi
	jmp	.L898
.L935:
	incl	%r9d
	jmp	.L914
.L900:
	leaq	104(%rsp), %rdx
	leaq	144(%rsp), %rdi
.LEHB32:
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
.LEHE32:
	movq	152(%rsp), %rsi
	movq	160(%rsp), %rcx
	jmp	.L901
.L1083:
	movq	144(%rsp), %rdi
	subq	%rdi, %rsi
	subq	%rdi, %rcx
	cmpq	$16, %rsi
	je	.L902
	testq	%rdi, %rdi
	je	.L896
	jmp	.L905
.L944:
	addq	$32, %rsi
	cmpq	%rsi, %rdx
	jne	.L946
.L938:
	movq	%rcx, %rax
	subq	%rsi, %rax
	cmpq	$16, %rax
	je	.L1085
	cmpq	$24, %rax
	je	.L948
	cmpq	$8, %rax
	jne	.L951
	movl	144(%rsp), %eax
.L949:
	movl	(%rsi), %edx
	movl	4(%rsi), %r8d
	movl	%eax, %edi
	cmpl	%eax, %edx
	je	.L939
	cmpl	%eax, %r8d
	je	.L939
	movl	148(%rsp), %eax
	cmpl	%eax, %r8d
	je	.L939
	cmpl	%eax, %edx
	je	.L939
.L951:
	movq	%rcx, %rsi
	jmp	.L953
.L893:
	leaq	144(%rsp), %rdx
	leaq	112(%rsp), %rdi
	movq	%r14, %rsi
.LEHB33:
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
.LEHE33:
	movq	120(%rsp), %r14
	movq	128(%rsp), %rsi
	jmp	.L892
.L1080:
	movq	%r12, %rdi
	movq	%r9, 88(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	88(%rsp), %r9
	jmp	.L883
.L1081:
	movq	%r12, %rdi
	movq	%r9, 88(%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rcx
	movq	88(%rsp), %r9
	jmp	.L884
.L985:
	xorl	%eax, %eax
	xorl	%r11d, %r11d
	xorl	%r9d, %r9d
	movl	$-1, %r10d
	jmp	.L912
.L987:
	vmovd	%xmm5, %r10d
	jmp	.L914
.L990:
	vmovd	%xmm6, %r10d
	jmp	.L914
.L961:
	leaq	144(%rsp), %rdx
	leaq	80(%rbx), %rdi
.LEHB34:
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJRKS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
.LEHE34:
	jmp	.L856
.L940:
	movl	16(%rsi), %r10d
	movl	20(%rsi), %r9d
	cmpl	%r10d, %r8d
	sete	%r11b
	cmpl	%r9d, %r8d
	sete	%r12b
	orb	%r12b, %r11b
	jne	.L1000
	cmpl	%r9d, %eax
	sete	%r9b
	cmpl	%r10d, %eax
	sete	%r10b
	orb	%r10b, %r9b
	je	.L942
.L1000:
	addq	$16, %rsi
	jmp	.L939
.L891:
	movq	%r12, %rdx
	xorl	%esi, %esi
	xorl	%edi, %edi
	call	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt4pairIiiESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_
	jmp	.L856
.L942:
	movl	28(%rsi), %r10d
	movl	24(%rsi), %r9d
	cmpl	%r10d, %eax
	sete	%r11b
	cmpl	%r9d, %eax
	sete	%r12b
	orb	%r12b, %r11b
	jne	.L1001
	cmpl	%r9d, %r8d
	sete	%r9b
	cmpl	%r10d, %r8d
	sete	%r10b
	orb	%r10b, %r9b
	je	.L944
.L1001:
	addq	$24, %rsi
	jmp	.L939
.L1060:
	call	__stack_chk_fail@PLT
.L948:
	movl	144(%rsp), %eax
	movl	4(%rsi), %r9d
	movl	(%rsi), %r8d
	movl	%eax, %edi
	cmpl	%eax, %r9d
	je	.L939
	cmpl	%eax, %r8d
	je	.L939
	movl	148(%rsp), %edx
	cmpl	%edx, %r9d
	je	.L939
	cmpl	%edx, %r8d
	je	.L939
	addq	$8, %rsi
.L947:
	movl	(%rsi), %r9d
	movl	4(%rsi), %r8d
	movl	%eax, %edi
	cmpl	%eax, %r9d
	je	.L939
	cmpl	%eax, %r8d
	je	.L939
	movl	148(%rsp), %edx
	cmpl	%edx, %r9d
	je	.L939
	cmpl	%edx, %r8d
	je	.L939
	addq	$8, %rsi
	jmp	.L949
.L1085:
	movl	144(%rsp), %eax
	jmp	.L947
.L997:
	endbr64
	movq	%rax, %r12
	vzeroupper
	jmp	.L975
.L998:
	endbr64
	movq	%rax, %r12
	jmp	.L973
	.section	.gcc_except_table
.LLSDA5705:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE5705-.LLSDACSB5705
.LLSDACSB5705:
	.uleb128 .LEHB31-.LFB5705
	.uleb128 .LEHE31-.LEHB31
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB32-.LFB5705
	.uleb128 .LEHE32-.LEHB32
	.uleb128 .L998-.LFB5705
	.uleb128 0
	.uleb128 .LEHB33-.LFB5705
	.uleb128 .LEHE33-.LEHB33
	.uleb128 .L997-.LFB5705
	.uleb128 0
	.uleb128 .LEHB34-.LFB5705
	.uleb128 .LEHE34-.LEHB34
	.uleb128 0
	.uleb128 0
.LLSDACSE5705:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC5705
	.type	_Z6mutateR7Circuit.cold, @function
_Z6mutateR7Circuit.cold:
.LFSB5705:
.L973:
	.cfi_def_cfa 6, 16
	.cfi_offset 3, -56
	.cfi_offset 6, -16
	.cfi_offset 12, -48
	.cfi_offset 13, -40
	.cfi_offset 14, -32
	.cfi_offset 15, -24
	movq	144(%rsp), %rdi
	movq	160(%rsp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L1057
	vzeroupper
	call	_ZdlPvm@PLT
.L975:
	movq	112(%rsp), %rdi
	movq	128(%rsp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L976
	call	_ZdlPvm@PLT
.L976:
	movq	%r12, %rdi
.LEHB35:
	call	_Unwind_Resume@PLT
.LEHE35:
.L1057:
	vzeroupper
	jmp	.L975
	.cfi_endproc
.LFE5705:
	.section	.gcc_except_table
.LLSDAC5705:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSEC5705-.LLSDACSBC5705
.LLSDACSBC5705:
	.uleb128 .LEHB35-.LCOLDB58
	.uleb128 .LEHE35-.LEHB35
	.uleb128 0
	.uleb128 0
.LLSDACSEC5705:
	.section	.text.unlikely
	.text
	.size	_Z6mutateR7Circuit, .-_Z6mutateR7Circuit
	.section	.text.unlikely
	.size	_Z6mutateR7Circuit.cold, .-_Z6mutateR7Circuit.cold
.LCOLDE58:
	.text
.LHOTE58:
	.section	.text.unlikely
.LCOLDB59:
	.text
.LHOTB59:
	.p2align 4
	.globl	_Z13randomcircuitv
	.type	_Z13randomcircuitv, @function
_Z13randomcircuitv:
.LFB5667:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5667
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
	vpxor	%xmm0, %xmm0, %xmm0
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	xorl	%ebp, %ebp
	subq	$72, %rsp
	.cfi_def_cfa_offset 128
	movslq	rounds(%rip), %rsi
	xorl	%ebx, %ebx
	movq	%rdi, 16(%rsp)
	movq	%fs:40, %rax
	movq	%rax, 56(%rsp)
	xorl	%eax, %eax
	vmovdqu	%xmm0, (%rdi)
	movq	$0, 16(%rdi)
	testq	%rsi, %rsi
	jne	.L1134
.L1087:
	leaq	rng(%rip), %rsi
	movabsq	$6148914691236517205, %r14
	movabsq	$8202884508482404352, %r13
	movl	budget(%rip), %r12d
.L1099:
	movabsq	$-2270628950310912, %r15
	.p2align 4
	.p2align 3
.L1101:
	cmpq	%rbp, %rbx
	je	.L1115
	movq	%rbx, %rdx
	xorl	%ecx, %ecx
	.p2align 4
	.p2align 3
.L1107:
	movq	88(%rdx), %rax
	subq	80(%rdx), %rax
	addq	$104, %rdx
	sarq	$3, %rax
	addl	%eax, %ecx
	cmpq	%rbp, %rdx
	jne	.L1107
	cmpl	%r12d, %ecx
	jle	.L1135
.L1108:
	movq	2496+rng(%rip), %rax
	movslq	rounds(%rip), %rcx
	cmpq	$311, %rax
	ja	.L1136
.L1100:
	leaq	1(%rax), %rdi
	movq	(%rsi,%rax,8), %rax
	movq	%rdi, 2496+rng(%rip)
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%r14, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%r13, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%r15, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	%rcx
	movslq	%edx, %rcx
	imulq	$104, %rcx, %rcx
	addq	%rbx, %rcx
	movq	88(%rcx), %r8
	movq	80(%rcx), %r9
	cmpq	%r9, %r8
	je	.L1101
	movq	%r8, %r15
	subq	%r9, %r15
	sarq	$3, %r15
	cmpq	$311, %rdi
	ja	.L1137
.L1102:
	leaq	1(%rdi), %rax
	movslq	%r15d, %r15
	movq	%rax, 2496+rng(%rip)
	movq	(%rsi,%rdi,8), %rax
	movabsq	$-2270628950310912, %rdi
	movq	%rax, %rdx
	shrq	$29, %rdx
	andq	%r14, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$17, %rdx
	andq	%r13, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	salq	$37, %rdx
	andq	%rdi, %rdx
	xorq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$43, %rdx
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	%r15
	movslq	%edx, %rdx
	salq	$3, %rdx
	leaq	8(%r9,%rdx), %rax
	leaq	(%r9,%rdx), %r10
	cmpq	%rax, %r8
	je	.L1104
	movq	%r8, %r11
	subq	%rax, %r11
	movq	%r11, %rdi
	sarq	$3, %rdi
	testq	%r11, %r11
	jle	.L1104
	leaq	8(%r9,%rdx), %r9
	salq	$3, %rdi
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L1105:
	movq	(%r9,%rax), %rdx
	movq	%rdx, (%r10,%rax)
	addq	$8, %rax
	cmpq	%rdi, %rax
	jne	.L1105
.L1104:
	subq	$8, %r8
	movq	%r8, 88(%rcx)
	jmp	.L1099
	.p2align 4
	.p2align 3
.L1136:
	movq	%rsi, %rdi
	movl	%ecx, (%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	leaq	rng(%rip), %rsi
	movq	2496+rng(%rip), %rax
	movslq	(%rsp), %rcx
	jmp	.L1100
	.p2align 4
	.p2align 3
.L1115:
	xorl	%ecx, %ecx
	cmpl	%r12d, %ecx
	jg	.L1108
.L1135:
	movq	56(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1138
	movq	16(%rsp), %rax
	addq	$72, %rsp
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
.L1134:
	.cfi_restore_state
.LEHB36:
	call	_ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm
	movq	16(%rsp), %rax
	movq	8(%rax), %rsi
	movq	(%rax), %rbx
	movq	%rsi, 8(%rsp)
	cmpq	%rsi, %rbx
	je	.L1139
	leaq	32(%rsp), %r15
	leaq	rng(%rip), %r12
	movabsq	$8202884508482404352, %r13
	movabsq	$-2270628950310912, %r14
	.p2align 4
	.p2align 3
.L1096:
	movl	nq(%rip), %eax
	movq	2496+rng(%rip), %rdi
	xorl	%ebp, %ebp
	movabsq	$-6148914691236517205, %rsi
	testl	%eax, %eax
	jg	.L1090
	jmp	.L1098
	.p2align 4
	.p2align 3
.L1089:
	movq	(%r12,%rax,8), %rcx
	leaq	1(%rax), %rdi
	movabsq	$6148914691236517205, %rdx
	movq	%rdi, 2496+rng(%rip)
	movq	%rcx, %rax
	shrq	$29, %rax
	andq	%rdx, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$17, %rax
	andq	%r13, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	salq	$37, %rax
	andq	%r14, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	shrq	$43, %rax
	xorq	%rax, %rcx
	movq	%rcx, %rax
	mulq	%rsi
	shrq	$2, %rdx
	leaq	(%rdx,%rdx,2), %rax
	addq	%rax, %rax
	subq	%rax, %rcx
	movl	%ecx, (%rbx,%rbp,4)
	incq	%rbp
	cmpl	%ebp, nq(%rip)
	jle	.L1098
.L1090:
	movq	%rdi, %rax
	cmpq	$311, %rdi
	jbe	.L1089
	movq	%r12, %rdi
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rax
	movabsq	$-6148914691236517205, %rsi
	jmp	.L1089
	.p2align 4
	.p2align 3
.L1098:
	leaq	80(%rbx), %rax
	movl	$5, %ebp
	movq	%rax, (%rsp)
.L1095:
	movq	%r15, %rdi
	call	_Z8matchingv
.LEHE36:
	movq	32(%rsp), %rdi
	movq	40(%rsp), %rdx
	movq	88(%rbx), %rax
	subq	80(%rbx), %rax
	subq	%rdi, %rdx
	cmpq	%rax, %rdx
	ja	.L1140
.L1091:
	testq	%rdi, %rdi
	je	.L1092
	movq	48(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	decl	%ebp
	jne	.L1095
	addq	$104, %rbx
	cmpq	%rbx, 8(%rsp)
	jne	.L1096
.L1141:
	movq	16(%rsp), %rax
	movq	(%rax), %rbx
	movq	8(%rax), %rbp
	jmp	.L1087
	.p2align 4
	.p2align 3
.L1092:
	decl	%ebp
	jne	.L1095
	addq	$104, %rbx
	cmpq	%rbx, 8(%rsp)
	jne	.L1096
	jmp	.L1141
	.p2align 4
	.p2align 3
.L1140:
	movq	(%rsp), %rdi
	movq	%r15, %rsi
.LEHB37:
	call	_ZNSt6vectorISt4pairIiiESaIS1_EEaSERKS3_.isra.0
.LEHE37:
	movq	32(%rsp), %rdi
	jmp	.L1091
.L1137:
	movq	%rsi, %rdi
	movq	%rcx, 24(%rsp)
	movq	%r9, 8(%rsp)
	movq	%r8, (%rsp)
	call	_ZNSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EE11_M_gen_randEv
	movq	2496+rng(%rip), %rdi
	leaq	rng(%rip), %rsi
	movq	24(%rsp), %rcx
	movq	8(%rsp), %r9
	movq	(%rsp), %r8
	jmp	.L1102
.L1139:
	movq	%rbx, %rbp
	jmp	.L1087
.L1138:
	call	__stack_chk_fail@PLT
.L1117:
	endbr64
	movq	%rax, %rbp
	jmp	.L1109
.L1116:
	endbr64
	movq	%rax, %rbp
	vzeroupper
	jmp	.L1111
	.section	.gcc_except_table
.LLSDA5667:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE5667-.LLSDACSB5667
.LLSDACSB5667:
	.uleb128 .LEHB36-.LFB5667
	.uleb128 .LEHE36-.LEHB36
	.uleb128 .L1116-.LFB5667
	.uleb128 0
	.uleb128 .LEHB37-.LFB5667
	.uleb128 .LEHE37-.LEHB37
	.uleb128 .L1117-.LFB5667
	.uleb128 0
.LLSDACSE5667:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC5667
	.type	_Z13randomcircuitv.cold, @function
_Z13randomcircuitv.cold:
.LFSB5667:
.L1109:
	.cfi_def_cfa_offset 128
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	movq	32(%rsp), %rdi
	movq	48(%rsp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L1132
	vzeroupper
	call	_ZdlPvm@PLT
.L1111:
	movq	16(%rsp), %rdi
	call	_ZNSt6vectorI5LayerSaIS0_EED1Ev
	movq	%rbp, %rdi
.LEHB38:
	call	_Unwind_Resume@PLT
.LEHE38:
.L1132:
	vzeroupper
	jmp	.L1111
	.cfi_endproc
.LFE5667:
	.section	.gcc_except_table
.LLSDAC5667:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSEC5667-.LLSDACSBC5667
.LLSDACSBC5667:
	.uleb128 .LEHB38-.LCOLDB59
	.uleb128 .LEHE38-.LEHB38
	.uleb128 0
	.uleb128 0
.LLSDACSEC5667:
	.section	.text.unlikely
	.text
	.size	_Z13randomcircuitv, .-_Z13randomcircuitv
	.section	.text.unlikely
	.size	_Z13randomcircuitv.cold, .-_Z13randomcircuitv.cold
.LCOLDE59:
	.text
.LHOTE59:
	.section	.text.unlikely
.LCOLDB60:
	.text
.LHOTB60:
	.p2align 4
	.globl	_Z4loadNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE
	.type	_Z4loadNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE, @function
_Z4loadNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE:
.LFB5704:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5704
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
	movq	%rsi, %rbx
	andq	$-32, %rsp
	subq	$640, %rsp
	movq	%rdi, 32(%rsp)
	leaq	96(%rsp), %r14
	movq	%fs:40, %rax
	movq	%rax, 632(%rsp)
	xorl	%eax, %eax
	leaq	352(%rsp), %rax
	movq	%rax, %rdi
	movq	%rax, %r13
	movq	%rax, 16(%rsp)
	call	_ZNSt8ios_baseC2Ev@PLT
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movw	$0, 576(%rsp)
	movq	%rax, 352(%rsp)
	movq	8+_ZTTSt14basic_ifstreamIcSt11char_traitsIcEE(%rip), %rax
	vmovdqu	%ymm0, 584(%rsp)
	movq	$0, 568(%rsp)
	xorl	%esi, %esi
	movq	16+_ZTTSt14basic_ifstreamIcSt11char_traitsIcEE(%rip), %rcx
	movq	%rax, 96(%rsp)
	movq	-24(%rax), %rax
	movq	%rcx, 96(%rsp,%rax)
	movq	8+_ZTTSt14basic_ifstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	$0, 104(%rsp)
	movq	-24(%rax), %rdi
	addq	%r14, %rdi
	vzeroupper
.LEHB39:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE4initEPSt15basic_streambufIcS1_E@PLT
.LEHE39:
	leaq	24+_ZTVSt14basic_ifstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	%rax, 96(%rsp)
	addq	$40, %rax
	movq	%rax, 352(%rsp)
	leaq	112(%rsp), %rax
	movq	%rax, %rdi
	movq	%rax, %r15
	movq	%rax, 24(%rsp)
.LEHB40:
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEEC1Ev@PLT
.LEHE40:
	movq	%r15, %rsi
	movq	%r13, %rdi
.LEHB41:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE4initEPSt15basic_streambufIcS1_E@PLT
	movq	(%rbx), %rsi
	movq	24(%rsp), %rdi
	movl	$8, %edx
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEE4openEPKcSt13_Ios_Openmode@PLT
	movq	96(%rsp), %rdx
	movq	-24(%rdx), %rdi
	addq	%r14, %rdi
	testq	%rax, %rax
	je	.L1182
	xorl	%esi, %esi
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE5clearESt12_Ios_Iostate@PLT
.LEHE41:
.L1144:
	leaq	68(%rsp), %rsi
	movq	%r14, %rdi
.LEHB42:
	call	_ZNSirsERi@PLT
	movq	%rax, %rdi
	leaq	72(%rsp), %rsi
	call	_ZNSirsERi@PLT
.LEHE42:
	movq	32(%rsp), %rax
	movslq	72(%rsp), %rsi
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqu	%xmm0, (%rax)
	movq	$0, 16(%rax)
	testq	%rsi, %rsi
	jne	.L1183
.L1149:
	leaq	24+_ZTVSt14basic_ifstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	24(%rsp), %rdi
	movq	%rax, 96(%rsp)
	addq	$40, %rax
	movq	%rax, 352(%rsp)
	leaq	16+_ZTVSt13basic_filebufIcSt11char_traitsIcEE(%rip), %rax
	movq	%rax, 112(%rsp)
.LEHB43:
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEE5closeEv@PLT
.LEHE43:
.L1159:
	leaq	216(%rsp), %rdi
	call	_ZNSt12__basic_fileIcED1Ev@PLT
	leaq	16+_ZTVSt15basic_streambufIcSt11char_traitsIcEE(%rip), %rax
	leaq	168(%rsp), %rdi
	movq	%rax, 112(%rsp)
	call	_ZNSt6localeD1Ev@PLT
	movq	8+_ZTTSt14basic_ifstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	16+_ZTTSt14basic_ifstreamIcSt11char_traitsIcEE(%rip), %rcx
	movq	16(%rsp), %rdi
	movq	%rax, 96(%rsp)
	movq	-24(%rax), %rax
	movq	%rcx, 96(%rsp,%rax)
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	movq	$0, 104(%rsp)
	movq	%rax, 352(%rsp)
	call	_ZNSt8ios_baseD2Ev@PLT
	movq	632(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1184
	movq	32(%rsp), %rax
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
.L1183:
	.cfi_restore_state
	movq	%rax, %rdi
.LEHB44:
	call	_ZNSt6vectorI5LayerSaIS0_EE17_M_default_appendEm
	movq	32(%rsp), %rax
	movq	8(%rax), %rcx
	movq	(%rax), %rbx
	movq	%rcx, 48(%rsp)
	cmpq	%rbx, %rcx
	je	.L1149
	leaq	76(%rsp), %rax
	leaq	84(%rsp), %r15
	movq	%rax, 40(%rsp)
	leaq	80(%rsp), %rax
	movq	%rax, 56(%rsp)
	.p2align 4
	.p2align 3
.L1153:
	movl	68(%rsp), %eax
	movq	%rbx, %r13
	xorl	%r12d, %r12d
	testl	%eax, %eax
	jle	.L1157
	.p2align 4
	.p2align 3
.L1151:
	movq	%r13, %rsi
	movq	%r14, %rdi
	call	_ZNSirsERi@PLT
	incl	%r12d
	addq	$4, %r13
	cmpl	%r12d, 68(%rsp)
	jg	.L1151
.L1157:
	movq	40(%rsp), %rsi
	movq	%r14, %rdi
	call	_ZNSirsERi@PLT
	movl	76(%rsp), %edx
	xorl	%r12d, %r12d
	testl	%edx, %edx
	jg	.L1152
	jmp	.L1156
	.p2align 4
	.p2align 3
.L1185:
	movq	88(%rsp), %rax
	addq	$8, %rsi
	incl	%r12d
	movq	%rax, -8(%rsi)
	movq	%rsi, 88(%rbx)
	cmpl	%r12d, 76(%rsp)
	jle	.L1156
.L1152:
	movq	%r14, %rdi
	movq	56(%rsp), %rsi
	call	_ZNSirsERi@PLT
	movq	%rax, %rdi
	movq	%r15, %rsi
	call	_ZNSirsERi@PLT
	vmovd	80(%rsp), %xmm1
	movq	88(%rbx), %rsi
	vpinsrd	$1, 84(%rsp), %xmm1, %xmm0
	vmovq	%xmm0, 88(%rsp)
	cmpq	96(%rbx), %rsi
	jne	.L1185
	leaq	88(%rsp), %rdx
	leaq	80(%rbx), %rdi
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
.LEHE44:
	incl	%r12d
	cmpl	%r12d, 76(%rsp)
	jg	.L1152
	.p2align 4
	.p2align 3
.L1156:
	addq	$104, %rbx
	cmpq	%rbx, 48(%rsp)
	jne	.L1153
	jmp	.L1149
.L1182:
	movl	32(%rdi), %esi
	orl	$4, %esi
.LEHB45:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE5clearESt12_Ios_Iostate@PLT
.LEHE45:
	jmp	.L1144
.L1184:
	call	__stack_chk_fail@PLT
.L1170:
	endbr64
	movq	%rax, %rdi
	jmp	.L1158
.L1165:
	endbr64
	movq	%rax, %r12
	vzeroupper
	jmp	.L1161
.L1169:
	endbr64
	movq	%rax, %rbx
	jmp	.L1146
.L1168:
	endbr64
	movq	%rax, %rbx
	vzeroupper
	jmp	.L1147
.L1167:
	endbr64
	movq	%rax, %rbx
	vzeroupper
	jmp	.L1148
.L1166:
	endbr64
	movq	%rax, %r12
	jmp	.L1160
	.section	.gcc_except_table
	.align 4
.LLSDA5704:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATT5704-.LLSDATTD5704
.LLSDATTD5704:
	.byte	0x1
	.uleb128 .LLSDACSE5704-.LLSDACSB5704
.LLSDACSB5704:
	.uleb128 .LEHB39-.LFB5704
	.uleb128 .LEHE39-.LEHB39
	.uleb128 .L1167-.LFB5704
	.uleb128 0
	.uleb128 .LEHB40-.LFB5704
	.uleb128 .LEHE40-.LEHB40
	.uleb128 .L1168-.LFB5704
	.uleb128 0
	.uleb128 .LEHB41-.LFB5704
	.uleb128 .LEHE41-.LEHB41
	.uleb128 .L1169-.LFB5704
	.uleb128 0
	.uleb128 .LEHB42-.LFB5704
	.uleb128 .LEHE42-.LEHB42
	.uleb128 .L1165-.LFB5704
	.uleb128 0
	.uleb128 .LEHB43-.LFB5704
	.uleb128 .LEHE43-.LEHB43
	.uleb128 .L1170-.LFB5704
	.uleb128 0x1
	.uleb128 .LEHB44-.LFB5704
	.uleb128 .LEHE44-.LEHB44
	.uleb128 .L1166-.LFB5704
	.uleb128 0
	.uleb128 .LEHB45-.LFB5704
	.uleb128 .LEHE45-.LEHB45
	.uleb128 .L1169-.LFB5704
	.uleb128 0
.LLSDACSE5704:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATT5704:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC5704
	.type	_Z4loadNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold, @function
_Z4loadNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold:
.LFSB5704:
.L1158:
	.cfi_def_cfa 6, 16
	.cfi_offset 3, -56
	.cfi_offset 6, -16
	.cfi_offset 12, -48
	.cfi_offset 13, -40
	.cfi_offset 14, -32
	.cfi_offset 15, -24
	vzeroupper
	call	__cxa_begin_catch@PLT
	call	__cxa_end_catch@PLT
	jmp	.L1159
.L1160:
	movq	32(%rsp), %rdi
	vzeroupper
	call	_ZNSt6vectorI5LayerSaIS0_EED1Ev
.L1161:
	movq	%r14, %rdi
	call	_ZNSt14basic_ifstreamIcSt11char_traitsIcEED1Ev@PLT
	movq	%r12, %rdi
.LEHB46:
	call	_Unwind_Resume@PLT
.L1146:
	movq	24(%rsp), %rdi
	vzeroupper
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEED1Ev@PLT
.L1147:
	movq	8+_ZTTSt14basic_ifstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	16+_ZTTSt14basic_ifstreamIcSt11char_traitsIcEE(%rip), %rcx
	movq	%rax, 96(%rsp)
	movq	-24(%rax), %rax
	movq	%rcx, 96(%rsp,%rax)
	movq	$0, 104(%rsp)
.L1148:
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	movq	16(%rsp), %rdi
	movq	%rax, 352(%rsp)
	call	_ZNSt8ios_baseD2Ev@PLT
	movq	%rbx, %rdi
	call	_Unwind_Resume@PLT
.LEHE46:
	.cfi_endproc
.LFE5704:
	.section	.gcc_except_table
	.align 4
.LLSDAC5704:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATTC5704-.LLSDATTDC5704
.LLSDATTDC5704:
	.byte	0x1
	.uleb128 .LLSDACSEC5704-.LLSDACSBC5704
.LLSDACSBC5704:
	.uleb128 .LEHB46-.LCOLDB60
	.uleb128 .LEHE46-.LEHB46
	.uleb128 0
	.uleb128 0
.LLSDACSEC5704:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATTC5704:
	.section	.text.unlikely
	.text
	.size	_Z4loadNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE, .-_Z4loadNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE
	.section	.text.unlikely
	.size	_Z4loadNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold, .-_Z4loadNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold
.LCOLDE60:
	.text
.LHOTE60:
	.section	.text.unlikely
.LCOLDB69:
	.text
.LHOTB69:
	.p2align 4
	.globl	_Z5setupi
	.type	_Z5setupi, @function
_Z5setupi:
.LFB5631:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5631
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
	movl	%edi, %r15d
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movl	$96, %edi
	subq	$184, %rsp
	.cfi_def_cfa_offset 240
	movq	%fs:40, %rax
	movq	%rax, 168(%rsp)
	xorl	%eax, %eax
	leaq	80(%rsp), %rax
	movq	$8, 72(%rsp)
	movb	$0, 88(%rsp)
	movl	$1684632167, 112(%rsp)
	movq	%rax, 64(%rsp)
	movabsq	$3905028131708494188, %rax
	movw	$12338, 116(%rsp)
	movq	$6, 104(%rsp)
	movq	%rax, 80(%rsp)
	leaq	112(%rsp), %rax
	movb	$0, 118(%rsp)
	movq	$8, 136(%rsp)
	movq	%rax, 96(%rsp)
	leaq	144(%rsp), %rax
	movb	$0, 152(%rsp)
	movq	%rax, 128(%rsp)
	movabsq	$4049129034723455586, %rax
	movq	%rax, 144(%rsp)
.LEHB47:
	call	_Znwm@PLT
.LEHE47:
	movq	64(%rsp), %r13
	leaq	16(%rax), %rdi
	movq	%rax, %rbp
	movq	72(%rsp), %r12
	movq	%rdi, (%rax)
	movq	%r13, %rax
	addq	%r12, %rax
	je	.L1297
	testq	%r13, %r13
	je	.L1286
.L1297:
	movq	%r12, 56(%rsp)
	cmpq	$15, %r12
	ja	.L1352
	cmpq	$1, %r12
	jne	.L1353
	movzbl	0(%r13), %eax
	movb	%al, 16(%rbp)
.L1194:
	movq	%r12, 8(%rbp)
	movb	$0, (%rdi,%r12)
	movq	96(%rsp), %r13
	leaq	48(%rbp), %rdi
	leaq	32(%rbp), %rbx
	movq	%rdi, 32(%rbp)
	movq	104(%rsp), %r12
	movq	%r13, %rax
	addq	%r12, %rax
	je	.L1298
	testq	%r13, %r13
	je	.L1190
.L1298:
	movq	%r12, 56(%rsp)
	cmpq	$15, %r12
	ja	.L1354
	cmpq	$1, %r12
	je	.L1201
	testq	%r12, %r12
	jne	.L1202
.L1200:
	movq	%r12, 40(%rbp)
	movb	$0, (%rdi,%r12)
	movq	128(%rsp), %r13
	movq	136(%rsp), %r12
	leaq	80(%rbp), %rdi
	leaq	64(%rbp), %rbx
	movq	%rdi, 64(%rbp)
	movq	%r13, %rax
	addq	%r12, %rax
	je	.L1203
	testq	%r13, %r13
	je	.L1190
.L1203:
	movq	%r12, 56(%rsp)
	cmpq	$15, %r12
	ja	.L1355
	cmpq	$1, %r12
	jne	.L1206
	movzbl	0(%r13), %eax
	movb	%al, 80(%rbp)
.L1207:
	movq	%r12, 72(%rbp)
	movb	$0, (%rdi,%r12)
	movslq	%r15d, %r12
	leaq	_Z6familyB5cxx11(%rip), %rdi
	movq	%r12, %rsi
	leaq	96(%rbp), %r13
	salq	$5, %rsi
	addq	%rbp, %rsi
.LEHB48:
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_assignERKS4_@PLT
.LEHE48:
	movq	%rbp, %rbx
	.p2align 4
	.p2align 3
.L1208:
	movq	(%rbx), %rdi
	leaq	16(%rbx), %rax
	cmpq	%rax, %rdi
	je	.L1218
	movq	16(%rbx), %rax
	addq	$32, %rbx
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
	cmpq	%r13, %rbx
	jne	.L1208
.L1220:
	movq	%rbp, %rdi
	movl	$96, %esi
	leaq	160(%rsp), %rbx
	call	_ZdlPvm@PLT
	leaq	64(%rsp), %rbp
.L1211:
	movq	-32(%rbx), %rdi
	subq	$32, %rbx
	leaq	16(%rbx), %rax
	cmpq	%rax, %rdi
	je	.L1221
	movq	16(%rbx), %rax
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
	cmpq	%rbp, %rbx
	jne	.L1211
.L1222:
	movq	.LC61(%rip), %rax
	movl	$12, %edi
	movl	$18, 72(%rsp)
	leaq	0(,%r12,4), %rbx
	movq	%rax, 64(%rsp)
.LEHB49:
	call	_Znwm@PLT
	movl	$12, %esi
	movq	%rax, %rdi
	movq	64(%rsp), %rax
	movq	%rax, (%rdi)
	movl	72(%rsp), %eax
	movl	%eax, 8(%rdi)
	movl	(%rdi,%rbx), %eax
	movl	%eax, nq(%rip)
	call	_ZdlPvm@PLT
	xorl	%eax, %eax
	cmpl	$1, %r15d
	setne	%al
	movl	$12, %edi
	movl	$90, 72(%rsp)
	leal	10(%rax,%rax), %eax
	movl	%eax, rounds(%rip)
	movq	.LC62(%rip), %rax
	movq	%rax, 64(%rsp)
	call	_Znwm@PLT
	movl	$12, %esi
	movq	%rax, %rdi
	movq	64(%rsp), %rax
	movq	%rax, (%rdi)
	movl	72(%rsp), %eax
	movl	%eax, 8(%rdi)
	movl	(%rdi,%rbx), %eax
	movl	%eax, budget(%rip)
	call	_ZdlPvm@PLT
	xorl	%eax, %eax
	cmpl	$1, %r15d
	sete	%al
	movl	$12, %edi
	movl	$5, 72(%rsp)
	addl	$8, %eax
	salq	$3, %r12
	movl	%eax, targetmin(%rip)
	movq	.LC63(%rip), %rax
	movq	%rax, 64(%rsp)
	call	_Znwm@PLT
	movl	$12, %esi
	movq	%rax, %rdi
	movq	64(%rsp), %rax
	movq	%rax, (%rdi)
	movl	72(%rsp), %eax
	movl	%eax, 8(%rdi)
	movl	(%rdi,%rbx), %eax
	movl	%eax, 4+targetmin(%rip)
	call	_ZdlPvm@PLT
	vmovapd	.LC64(%rip), %xmm0
	movl	$24, %edi
	movq	.LC65(%rip), %rax
	movq	%rax, 80(%rsp)
	vmovapd	%xmm0, 64(%rsp)
	call	_Znwm@PLT
	vmovdqa	64(%rsp), %xmm3
	movl	$24, %esi
	movq	%rax, %rdi
	vmovdqu	%xmm3, (%rax)
	movq	80(%rsp), %rax
	movq	%rax, 16(%rdi)
	vmovsd	(%rdi,%r12), %xmm0
	vmovsd	%xmm0, targetmean(%rip)
	call	_ZdlPvm@PLT
	vmovapd	.LC66(%rip), %xmm0
	movl	$24, %edi
	movq	.LC67(%rip), %rax
	movq	%rax, 80(%rsp)
	vmovapd	%xmm0, 64(%rsp)
	call	_Znwm@PLT
.LEHE49:
	vmovdqa	64(%rsp), %xmm4
	movl	$24, %esi
	movq	%rax, %rdi
	vmovdqu	%xmm4, (%rax)
	movq	80(%rsp), %rax
	movq	%rax, 16(%rdi)
	vmovsd	(%rdi,%r12), %xmm0
	vmovsd	%xmm0, 8+targetmean(%rip)
	call	_ZdlPvm@PLT
	testl	%r15d, %r15d
	je	.L1290
	cmpl	$1, %r15d
	sete	%bl
	sete	%r8b
	movzbl	%r8b, %r8d
	movzbl	%bl, %ebx
	addl	$3, %r8d
	leal	3(%rbx,%rbx), %ebx
.L1226:
	xorl	%eax, %eax
	cmpl	$2, %r15d
	movl	%r15d, 24(%rsp)
	movl	%r8d, %r15d
	sete	%al
	xorl	%r9d, %r9d
	leal	9(%rax,%rax,8), %eax
	movl	%eax, 20(%rsp)
	leaq	56(%rsp), %rax
	movq	%rax, 8(%rsp)
.L1227:
	leal	6(%r9), %ebp
	leal	(%rbx,%r9), %r13d
	leal	5(%r9), %ecx
	leal	4(%r9), %eax
	leal	3(%r9), %r14d
	xorl	%r12d, %r12d
.L1283:
	incl	%r12d
	leal	-6(%rbp), %r8d
	cmpl	%r15d, %r12d
	jl	.L1259
	movq	8+edges(%rip), %rsi
	cmpq	%rsi, 16+edges(%rip)
	leal	-5(%rbp), %r10d
	movl	%r8d, 56(%rsp)
	movl	%r10d, 60(%rsp)
	je	.L1260
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1261:
	leal	-4(%rbp), %r8d
	movl	%r10d, 56(%rsp)
	cmpq	16+edges(%rip), %rsi
	movl	%r8d, 60(%rsp)
	je	.L1262
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1263:
	cmpl	$3, %ebx
	jne	.L1356
.L1264:
	addl	%ebx, %ebp
	addl	%ebx, %r13d
	addl	%ebx, %ecx
	addl	%ebx, %eax
	addl	%ebx, %r14d
	cmpl	%r15d, %r12d
	jne	.L1283
	addl	$9, %r9d
	cmpl	20(%rsp), %r9d
	jne	.L1227
	movl	24(%rsp), %r15d
	cmpl	$2, %r15d
	je	.L1357
.L1186:
	movq	168(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1358
	addq	$184, %rsp
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
.L1353:
	.cfi_restore_state
	testq	%r12, %r12
	je	.L1194
	jmp	.L1196
	.p2align 4
	.p2align 3
.L1218:
	addq	$32, %rbx
	cmpq	%rbx, %r13
	jne	.L1208
	jmp	.L1220
	.p2align 4
	.p2align 3
.L1259:
	movq	8+edges(%rip), %rsi
	cmpq	%rsi, 16+edges(%rip)
	vmovd	%r8d, %xmm1
	vpinsrd	$1, %r13d, %xmm1, %xmm0
	vmovq	%xmm0, 56(%rsp)
	je	.L1228
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1229:
	leal	-5(%rbp), %r10d
	movl	%r8d, 56(%rsp)
	cmpq	%rsi, 16+edges(%rip)
	movl	%r10d, 60(%rsp)
	je	.L1359
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1231:
	leal	1(%r13), %edx
	vmovd	%r10d, %xmm2
	cmpq	%rsi, 16+edges(%rip)
	vpinsrd	$1, %edx, %xmm2, %xmm0
	vmovq	%xmm0, 56(%rsp)
	je	.L1232
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1233:
	leal	-4(%rbp), %r8d
	movl	%r10d, 56(%rsp)
	cmpq	%rsi, 16+edges(%rip)
	movl	%r8d, 60(%rsp)
	je	.L1360
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1235:
	leal	2(%r13), %edx
	movl	%r8d, 56(%rsp)
	cmpq	%rsi, 16+edges(%rip)
	movl	%edx, 60(%rsp)
	je	.L1236
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1237:
	leal	3(%rbp), %r10d
	cmpl	$3, %ebx
	jne	.L1361
.L1238:
	movl	%r10d, %ebp
	addl	%ebx, %r13d
	addl	%ebx, %ecx
	addl	%ebx, %eax
	addl	%ebx, %r14d
	jmp	.L1283
	.p2align 4
	.p2align 3
.L1221:
	cmpq	%rbp, %rbx
	jne	.L1211
	jmp	.L1222
	.p2align 4
	.p2align 3
.L1356:
	movq	8+edges(%rip), %rsi
	cmpq	%rsi, 16+edges(%rip)
	movl	%r8d, 56(%rsp)
	movl	%r14d, 60(%rsp)
	je	.L1265
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1266:
	cmpl	$4, %ebx
	je	.L1264
	movq	8+edges(%rip), %rsi
	cmpq	16+edges(%rip), %rsi
	movl	%r14d, 56(%rsp)
	movl	%eax, 60(%rsp)
	je	.L1267
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1268:
	cmpl	$5, %ebx
	je	.L1264
	movq	8+edges(%rip), %rsi
	cmpq	16+edges(%rip), %rsi
	movl	%eax, 56(%rsp)
	movl	%ecx, 60(%rsp)
	je	.L1269
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1270:
	cmpl	$6, %ebx
	je	.L1264
	movq	8+edges(%rip), %rsi
	cmpq	%rsi, 16+edges(%rip)
	movl	%ecx, 56(%rsp)
	movl	%ebp, 60(%rsp)
	je	.L1271
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1272:
	cmpl	$8, %ebx
	jne	.L1264
	movq	8+edges(%rip), %rsi
	cmpq	%rsi, 16+edges(%rip)
	leal	1(%rbp), %edx
	movl	%ebp, 56(%rsp)
	movl	%edx, 60(%rsp)
	je	.L1362
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
	jmp	.L1264
.L1290:
	movl	$2, %r8d
	movl	$8, %ebx
	jmp	.L1226
.L1201:
	movzbl	0(%r13), %eax
	movb	%al, 48(%rbp)
	jmp	.L1200
.L1206:
	testq	%r12, %r12
	je	.L1207
	jmp	.L1205
	.p2align 4
	.p2align 3
.L1354:
	leaq	56(%rsp), %rsi
	xorl	%edx, %edx
	movq	%rbx, %rdi
.LEHB50:
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_createERmm@PLT
	movq	%rax, %rdi
	movq	%rax, 32(%rbp)
	movq	56(%rsp), %rax
	movq	%rax, 48(%rbp)
.L1202:
	movq	%r12, %rdx
	movq	%r13, %rsi
	call	memcpy@PLT
	movq	56(%rsp), %r12
	movq	32(%rbp), %rdi
	jmp	.L1200
.L1355:
	leaq	56(%rsp), %rsi
	xorl	%edx, %edx
	movq	%rbx, %rdi
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_createERmm@PLT
.LEHE50:
	movq	%rax, %rdi
	movq	%rax, 64(%rbp)
	movq	56(%rsp), %rax
	movq	%rax, 80(%rbp)
.L1205:
	movq	%r12, %rdx
	movq	%r13, %rsi
	call	memcpy@PLT
	movq	56(%rsp), %r12
	movq	64(%rbp), %rdi
	jmp	.L1207
.L1352:
	leaq	56(%rsp), %rsi
	xorl	%edx, %edx
	movq	%rbp, %rdi
.LEHB51:
	call	_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE9_M_createERmm@PLT
.LEHE51:
	movq	%rax, %rdi
	movq	%rax, 0(%rbp)
	movq	56(%rsp), %rax
	movq	%rax, 16(%rbp)
.L1196:
	movq	%r12, %rdx
	movq	%r13, %rsi
	call	memcpy@PLT
	movq	56(%rsp), %r12
	movq	0(%rbp), %rdi
	jmp	.L1194
.L1361:
	movq	8+edges(%rip), %rsi
	cmpq	16+edges(%rip), %rsi
	movl	%r8d, 56(%rsp)
	movl	%r14d, 60(%rsp)
	je	.L1363
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1240:
	leal	3(%r13), %edx
	movl	%r14d, 56(%rsp)
	cmpq	%rsi, 16+edges(%rip)
	movl	%edx, 60(%rsp)
	je	.L1241
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1242:
	leal	4(%rbp), %r10d
	cmpl	$4, %ebx
	je	.L1238
	movq	8+edges(%rip), %rsi
	cmpq	16+edges(%rip), %rsi
	movl	%r14d, 56(%rsp)
	movl	%eax, 60(%rsp)
	je	.L1364
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1244:
	leal	4(%r13), %edx
	movl	%eax, 56(%rsp)
	cmpq	16+edges(%rip), %rsi
	movl	%edx, 60(%rsp)
	je	.L1245
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1246:
	leal	5(%rbp), %r10d
	cmpl	$5, %ebx
	je	.L1238
	movq	8+edges(%rip), %rsi
	cmpq	%rsi, 16+edges(%rip)
	movl	%eax, 56(%rsp)
	movl	%ecx, 60(%rsp)
	je	.L1365
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1248:
	leal	5(%r13), %edx
	movl	%ecx, 56(%rsp)
	cmpq	%rsi, 16+edges(%rip)
	movl	%edx, 60(%rsp)
	je	.L1249
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1250:
	leal	6(%rbp), %r10d
	cmpl	$6, %ebx
	je	.L1238
	movq	8+edges(%rip), %rsi
	cmpq	16+edges(%rip), %rsi
	movl	%ecx, 56(%rsp)
	movl	%ebp, 60(%rsp)
	je	.L1366
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1252:
	leal	0(%rbp,%rbx), %r10d
	movl	%ebp, 56(%rsp)
	cmpq	16+edges(%rip), %rsi
	movl	%r10d, 60(%rsp)
	je	.L1253
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1254:
	cmpl	$8, %ebx
	jne	.L1238
	movq	8+edges(%rip), %rsi
	cmpq	%rsi, 16+edges(%rip)
	leal	1(%rbp), %r8d
	movl	%ebp, 56(%rsp)
	movl	%r8d, 60(%rsp)
	je	.L1367
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
.L1256:
	leal	7(%r13), %edx
	movl	%r8d, 56(%rsp)
	cmpq	16+edges(%rip), %rsi
	movl	%edx, 60(%rsp)
	je	.L1257
	movq	56(%rsp), %rdx
	addq	$8, %rsi
	movq	%rdx, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
	jmp	.L1238
	.p2align 4
	.p2align 3
.L1260:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 40(%rsp)
	movl	%eax, 36(%rsp)
	movl	%ecx, 32(%rsp)
	movl	%r10d, 28(%rsp)
.LEHB52:
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	40(%rsp), %r9d
	movl	36(%rsp), %eax
	movl	32(%rsp), %ecx
	movl	28(%rsp), %r10d
	movq	8+edges(%rip), %rsi
	jmp	.L1261
.L1262:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 40(%rsp)
	movl	%eax, 36(%rsp)
	movl	%ecx, 32(%rsp)
	movl	%r8d, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	40(%rsp), %r9d
	movl	36(%rsp), %eax
	movl	32(%rsp), %ecx
	movl	28(%rsp), %r8d
	jmp	.L1263
.L1359:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 40(%rsp)
	movl	%eax, 36(%rsp)
	movl	%ecx, 32(%rsp)
	movl	%r10d, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	28(%rsp), %r10d
	movl	32(%rsp), %ecx
	movl	36(%rsp), %eax
	movl	40(%rsp), %r9d
	movq	8+edges(%rip), %rsi
	jmp	.L1231
.L1228:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 40(%rsp)
	movl	%eax, 36(%rsp)
	movl	%ecx, 32(%rsp)
	movl	%r8d, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	40(%rsp), %r9d
	movl	36(%rsp), %eax
	movl	32(%rsp), %ecx
	movl	28(%rsp), %r8d
	movq	8+edges(%rip), %rsi
	jmp	.L1229
.L1265:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	36(%rsp), %r9d
	movl	32(%rsp), %eax
	movl	28(%rsp), %ecx
	jmp	.L1266
.L1267:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	36(%rsp), %r9d
	movl	32(%rsp), %eax
	movl	28(%rsp), %ecx
	jmp	.L1268
.L1269:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	36(%rsp), %r9d
	movl	32(%rsp), %eax
	movl	28(%rsp), %ecx
	jmp	.L1270
.L1357:
	movq	8+edges(%rip), %rsi
	cmpq	16+edges(%rip), %rsi
	movq	.LC68(%rip), %rax
	movq	%rax, 56(%rsp)
	je	.L1276
	movq	56(%rsp), %rax
	addq	$8, %rsi
	movq	%rax, -8(%rsi)
	movq	%rsi, 8+edges(%rip)
	jmp	.L1186
.L1271:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	36(%rsp), %r9d
	movl	32(%rsp), %eax
	movl	28(%rsp), %ecx
	jmp	.L1272
.L1362:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	28(%rsp), %ecx
	movl	32(%rsp), %eax
	movl	36(%rsp), %r9d
	jmp	.L1264
.L1360:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 40(%rsp)
	movl	%eax, 36(%rsp)
	movl	%ecx, 32(%rsp)
	movl	%r8d, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	28(%rsp), %r8d
	movl	32(%rsp), %ecx
	movl	36(%rsp), %eax
	movl	40(%rsp), %r9d
	movq	8+edges(%rip), %rsi
	jmp	.L1235
.L1232:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 40(%rsp)
	movl	%eax, 36(%rsp)
	movl	%ecx, 32(%rsp)
	movl	%r10d, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	40(%rsp), %r9d
	movl	36(%rsp), %eax
	movl	32(%rsp), %ecx
	movl	28(%rsp), %r10d
	movq	8+edges(%rip), %rsi
	jmp	.L1233
.L1365:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	28(%rsp), %ecx
	movl	32(%rsp), %eax
	movl	36(%rsp), %r9d
	movq	8+edges(%rip), %rsi
	jmp	.L1248
.L1363:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	28(%rsp), %ecx
	movl	32(%rsp), %eax
	movl	36(%rsp), %r9d
	movq	8+edges(%rip), %rsi
	jmp	.L1240
.L1236:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 40(%rsp)
	movl	%eax, 36(%rsp)
	movl	%ecx, 32(%rsp)
	movl	%r8d, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	40(%rsp), %r9d
	movl	36(%rsp), %eax
	movl	32(%rsp), %ecx
	movl	28(%rsp), %r8d
	jmp	.L1237
.L1276:
	leaq	56(%rsp), %rdx
	leaq	edges(%rip), %rdi
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	jmp	.L1186
.L1364:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	28(%rsp), %ecx
	movl	32(%rsp), %eax
	movl	36(%rsp), %r9d
	movq	8+edges(%rip), %rsi
	jmp	.L1244
.L1241:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	36(%rsp), %r9d
	movl	32(%rsp), %eax
	movl	28(%rsp), %ecx
	jmp	.L1242
.L1245:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	36(%rsp), %r9d
	movl	32(%rsp), %eax
	movl	28(%rsp), %ecx
	jmp	.L1246
.L1366:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	28(%rsp), %ecx
	movl	32(%rsp), %eax
	movl	36(%rsp), %r9d
	movq	8+edges(%rip), %rsi
	jmp	.L1252
.L1249:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 36(%rsp)
	movl	%eax, 32(%rsp)
	movl	%ecx, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	36(%rsp), %r9d
	movl	32(%rsp), %eax
	movl	28(%rsp), %ecx
	jmp	.L1250
.L1367:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 44(%rsp)
	movl	%eax, 40(%rsp)
	movl	%ecx, 36(%rsp)
	movl	%r10d, 32(%rsp)
	movl	%r8d, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	28(%rsp), %r8d
	movl	32(%rsp), %r10d
	movl	36(%rsp), %ecx
	movl	40(%rsp), %eax
	movl	44(%rsp), %r9d
	movq	8+edges(%rip), %rsi
	jmp	.L1256
.L1253:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 40(%rsp)
	movl	%eax, 36(%rsp)
	movl	%ecx, 32(%rsp)
	movl	%r10d, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movl	40(%rsp), %r9d
	movl	36(%rsp), %eax
	movl	32(%rsp), %ecx
	movl	28(%rsp), %r10d
	jmp	.L1254
.L1358:
	call	__stack_chk_fail@PLT
.L1257:
	movq	8(%rsp), %rdx
	leaq	edges(%rip), %rdi
	movl	%r9d, 40(%rsp)
	movl	%eax, 36(%rsp)
	movl	%ecx, 32(%rsp)
	movl	%r10d, 28(%rsp)
	call	_ZNSt6vectorISt4pairIiiESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
.LEHE52:
	movl	28(%rsp), %r10d
	movl	32(%rsp), %ecx
	movl	36(%rsp), %eax
	movl	40(%rsp), %r9d
	jmp	.L1238
.L1286:
	movq	%rbp, %rbx
.L1190:
	leaq	.LC0(%rip), %rdi
.LEHB53:
	call	_ZSt19__throw_logic_errorPKc@PLT
.LEHE53:
.L1294:
	endbr64
	movq	%rax, %rdi
	jmp	.L1213
.L1296:
	endbr64
	movq	%rax, %rdi
	jmp	.L1212
.L1295:
	endbr64
	movq	%rax, %r12
	jmp	.L1188
.L1292:
	endbr64
	movq	%rax, %r12
	jmp	.L1209
	.section	.gcc_except_table
	.align 4
.LLSDA5631:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATT5631-.LLSDATTD5631
.LLSDATTD5631:
	.byte	0x1
	.uleb128 .LLSDACSE5631-.LLSDACSB5631
.LLSDACSB5631:
	.uleb128 .LEHB47-.LFB5631
	.uleb128 .LEHE47-.LEHB47
	.uleb128 .L1295-.LFB5631
	.uleb128 0
	.uleb128 .LEHB48-.LFB5631
	.uleb128 .LEHE48-.LEHB48
	.uleb128 .L1292-.LFB5631
	.uleb128 0
	.uleb128 .LEHB49-.LFB5631
	.uleb128 .LEHE49-.LEHB49
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB50-.LFB5631
	.uleb128 .LEHE50-.LEHB50
	.uleb128 .L1294-.LFB5631
	.uleb128 0x1
	.uleb128 .LEHB51-.LFB5631
	.uleb128 .LEHE51-.LEHB51
	.uleb128 .L1296-.LFB5631
	.uleb128 0x1
	.uleb128 .LEHB52-.LFB5631
	.uleb128 .LEHE52-.LEHB52
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB53-.LFB5631
	.uleb128 .LEHE53-.LEHB53
	.uleb128 .L1294-.LFB5631
	.uleb128 0x1
.LLSDACSE5631:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATT5631:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC5631
	.type	_Z5setupi.cold, @function
_Z5setupi.cold:
.LFSB5631:
.L1212:
	.cfi_def_cfa_offset 240
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	movq	%rbp, %rbx
.L1213:
	vzeroupper
	call	__cxa_begin_catch@PLT
	movq	%rbp, %r12
.L1214:
	cmpq	%rbx, %r12
	je	.L1368
	movq	(%r12), %rdi
	leaq	16(%r12), %rax
	cmpq	%rax, %rdi
	je	.L1215
	movq	16(%r12), %rax
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
.L1215:
	addq	$32, %r12
	jmp	.L1214
.L1188:
	leaq	160(%rsp), %rbx
	vzeroupper
.L1189:
	leaq	64(%rsp), %rbp
.L1281:
	movq	-32(%rbx), %rdi
	subq	$32, %rbx
	leaq	16(%rbx), %rax
	cmpq	%rax, %rdi
	je	.L1280
	movq	16(%rbx), %rax
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
.L1280:
	cmpq	%rbp, %rbx
	jne	.L1281
	movq	%r12, %rdi
.LEHB54:
	call	_Unwind_Resume@PLT
.LEHE54:
.L1209:
	movq	%rbp, %rbx
	vzeroupper
.L1210:
	cmpq	%rbx, %r13
	je	.L1369
	movq	(%rbx), %rdi
	leaq	16(%rbx), %rax
	cmpq	%rax, %rdi
	je	.L1278
	movq	16(%rbx), %rax
	leaq	1(%rax), %rsi
	call	_ZdlPvm@PLT
.L1278:
	addq	$32, %rbx
	jmp	.L1210
.L1369:
	movl	$96, %esi
	movq	%rbp, %rdi
	leaq	160(%rsp), %rbx
	call	_ZdlPvm@PLT
	jmp	.L1189
.L1368:
.LEHB55:
	call	__cxa_rethrow@PLT
.LEHE55:
.L1293:
	endbr64
	movq	%rax, %r12
	vzeroupper
	call	__cxa_end_catch@PLT
	movl	$96, %esi
	movq	%rbp, %rdi
	call	_ZdlPvm@PLT
	leaq	160(%rsp), %rbx
	jmp	.L1189
	.cfi_endproc
.LFE5631:
	.section	.gcc_except_table
	.align 4
.LLSDAC5631:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATTC5631-.LLSDATTDC5631
.LLSDATTDC5631:
	.byte	0x1
	.uleb128 .LLSDACSEC5631-.LLSDACSBC5631
.LLSDACSBC5631:
	.uleb128 .LEHB54-.LCOLDB69
	.uleb128 .LEHE54-.LEHB54
	.uleb128 0
	.uleb128 0
	.uleb128 .LEHB55-.LCOLDB69
	.uleb128 .LEHE55-.LEHB55
	.uleb128 .L1293-.LCOLDB69
	.uleb128 0
.LLSDACSEC5631:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATTC5631:
	.section	.text.unlikely
	.text
	.size	_Z5setupi, .-_Z5setupi
	.section	.text.unlikely
	.size	_Z5setupi.cold, .-_Z5setupi.cold
.LCOLDE69:
	.text
.LHOTE69:
	.section	.text._ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_,"axG",@progbits,_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
	.type	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_, @function
_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_:
.LFB7083:
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
	movabsq	$288230376151711743, %rdx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %r14
	movq	(%rdi), %r13
	movq	%r14, %rax
	subq	%r13, %rax
	sarq	$5, %rax
	cmpq	%rdx, %rax
	je	.L1391
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
	jne	.L1383
	testq	%rax, %rax
	jne	.L1375
	xorl	%ebx, %ebx
	xorl	%edi, %edi
.L1381:
	vmovdqu	(%r15), %xmm2
	vmovdqu	16(%r15), %xmm3
	subq	%r12, %r14
	leaq	32(%rdi,%rdx), %r15
	leaq	(%r15,%r14), %rax
	vmovq	%rdi, %xmm1
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqa	%xmm0, (%rsp)
	vmovdqu	%xmm2, (%rdi,%rdx)
	vmovdqu	%xmm3, 16(%rdi,%rdx)
	testq	%rdx, %rdx
	jg	.L1392
	testq	%r14, %r14
	jg	.L1379
	testq	%r13, %r13
	jne	.L1390
.L1380:
	vmovdqa	(%rsp), %xmm4
	movq	%rbx, 16(%rbp)
	vmovdqu	%xmm4, 0(%rbp)
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
.L1392:
	.cfi_restore_state
	movq	%r13, %rsi
	call	memmove@PLT
	testq	%r14, %r14
	jg	.L1379
.L1390:
	movq	16(%rbp), %rsi
	movq	%r13, %rdi
	subq	%r13, %rsi
	call	_ZdlPvm@PLT
	jmp	.L1380
	.p2align 4
	.p2align 3
.L1379:
	movq	%r14, %rdx
	movq	%r12, %rsi
	movq	%r15, %rdi
	call	memcpy@PLT
	testq	%r13, %r13
	je	.L1380
	jmp	.L1390
	.p2align 4
	.p2align 3
.L1383:
	movabsq	$9223372036854775776, %rbx
.L1374:
	movq	%rbx, %rdi
	movq	%rdx, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rdx
	addq	%rax, %rbx
	jmp	.L1381
	.p2align 4
	.p2align 3
.L1375:
	movabsq	$288230376151711743, %rbx
	cmpq	%rbx, %rax
	cmovbe	%rax, %rbx
	salq	$5, %rbx
	jmp	.L1374
.L1391:
	leaq	.LC45(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7083:
	.size	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_, .-_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
	.section	.text.unlikely
.LCOLDB70:
	.text
.LHOTB70:
	.p2align 4
	.globl	_Z13getviolationsRK7CircuitSt5arrayIiLm3EE
	.type	_Z13getviolationsRK7CircuitSt5arrayIiLm3EE, @function
_Z13getviolationsRK7CircuitSt5arrayIiLm3EE:
.LFB5723:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5723
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
	movl	$1, %ebx
	andq	$-64, %rsp
	movq	%rsi, %rdi
	subq	$960, %rsp
	movl	nq(%rip), %r8d
	leaq	128(%rsp), %r13
	movl	%ecx, 88(%rsp)
	movq	%rdx, 80(%rsp)
	movl	%ecx, %ecx
	movq	%r13, %rsi
	movq	%fs:40, %rax
	movq	%rax, 952(%rsp)
	xorl	%eax, %eax
	shlx	%r8, %rbx, %rbx
	movl	%r8d, 72(%rsp)
	call	_Z7maprowsRK7CircuitPmSt5arrayIiLm3EE
	movl	72(%rsp), %r8d
	decq	%rbx
	testl	%r8d, %r8d
	jle	.L1394
	leal	-1(%r8), %eax
	cmpl	$6, %eax
	jbe	.L1419
	movslq	%r8d, %rax
	vpbroadcastq	%rbx, %zmm0
	vmovd	%r8d, %xmm4
	vmovdqa64	.LC4(%rip), %zmm10
	leaq	0(%r13,%rax,8), %rax
	vmovdqa64	.LC5(%rip), %zmm9
	vmovdqa64	.LC6(%rip), %zmm8
	movl	%r8d, %edx
	vmovdqu64	(%rax), %zmm5
	vpandq	(%rax), %zmm0, %zmm2
	shrl	$3, %edx
	vmovdqa64	.LC7(%rip), %zmm7
	vpsrlq	%xmm4, %zmm5, %zmm1
	vpsllq	%xmm4, %zmm2, %zmm2
	vmovdqa64	128(%rsp), %zmm5
	vporq	%zmm1, %zmm2, %zmm2
	vpandq	128(%rsp), %zmm0, %zmm1
	vmovdqa64	%zmm2, %zmm6
	vpsrlq	%xmm4, %zmm5, %zmm3
	vmovdqa64	%zmm2, %zmm5
	vpsllq	%xmm4, %zmm1, %zmm1
	vporq	%zmm3, %zmm1, %zmm1
	vpxorq	%zmm1, %zmm2, %zmm3
	vpermt2q	%zmm3, %zmm10, %zmm5
	vpermt2q	%zmm3, %zmm8, %zmm6
	vpermt2q	%zmm1, %zmm9, %zmm5
	vmovdqa64	%zmm5, 448(%rsp)
	vmovdqa64	%zmm1, %zmm5
	vpermt2q	%zmm6, %zmm7, %zmm5
	vmovdqa64	.LC8(%rip), %zmm6
	vmovdqa64	%zmm5, 512(%rsp)
	vmovdqa64	.LC9(%rip), %zmm5
	vpermt2q	%zmm2, %zmm6, %zmm3
	vpermt2q	%zmm1, %zmm5, %zmm3
	vmovdqa64	%zmm3, 576(%rsp)
	cmpl	$1, %edx
	je	.L1396
	vmovdqu64	64(%rax), %zmm2
	vmovdqa64	192(%rsp), %zmm3
	vpandq	%zmm2, %zmm0, %zmm1
	vpandq	192(%rsp), %zmm0, %zmm0
	vpsrlq	%xmm4, %zmm2, %zmm2
	vpsllq	%xmm4, %zmm1, %zmm1
	vporq	%zmm2, %zmm1, %zmm1
	vpsrlq	%xmm4, %zmm3, %zmm2
	vpsllq	%xmm4, %zmm0, %zmm0
	vporq	%zmm2, %zmm0, %zmm0
	vpxorq	%zmm1, %zmm0, %zmm2
	vpermi2q	%zmm2, %zmm1, %zmm10
	vpermi2q	%zmm2, %zmm1, %zmm8
	vpermi2q	%zmm1, %zmm2, %zmm6
	vpermi2q	%zmm0, %zmm10, %zmm9
	vpermi2q	%zmm8, %zmm0, %zmm7
	vpermi2q	%zmm0, %zmm6, %zmm5
	vmovdqa64	%zmm9, 640(%rsp)
	vmovdqa64	%zmm7, 704(%rsp)
	vmovdqa64	%zmm5, 768(%rsp)
.L1396:
	movl	%r8d, %eax
	leaq	448(%rsp), %r15
	andl	$-8, %eax
	movl	%eax, %edx
	cmpl	%eax, %r8d
	je	.L1398
.L1395:
	movl	%r8d, %edi
	leaq	448(%rsp), %r15
	subl	%eax, %edi
	leal	-1(%rdi), %ecx
	cmpl	$2, %ecx
	jbe	.L1399
	movslq	%r8d, %rsi
	vpbroadcastq	%rbx, %ymm0
	vmovd	%r8d, %xmm3
	vmovdqa	.LC10(%rip), %ymm4
	addq	%rax, %rsi
	leaq	(%rax,%rax,2), %rcx
	leaq	448(%rsp), %r15
	vmovdqu	128(%rsp,%rsi,8), %ymm2
	leaq	448(%rsp,%rcx,8), %rcx
	vpand	%ymm0, %ymm2, %ymm1
	vpsrlq	%xmm3, %ymm2, %ymm2
	vpsllq	%xmm3, %ymm1, %ymm1
	vpor	%ymm2, %ymm1, %ymm1
	vmovdqa	128(%rsp,%rax,8), %ymm2
	movl	%edi, %eax
	andl	$-4, %eax
	addl	%eax, %edx
	vpand	%ymm0, %ymm2, %ymm0
	vpsrlq	%xmm3, %ymm2, %ymm2
	vpsllq	%xmm3, %ymm0, %ymm0
	vpor	%ymm2, %ymm0, %ymm0
	vmovdqa	.LC11(%rip), %ymm2
	vpxor	%ymm0, %ymm1, %ymm3
	vpermi2q	%ymm3, %ymm1, %ymm4
	vpermi2q	%ymm0, %ymm4, %ymm2
	vmovdqa	%ymm2, (%rcx)
	vmovdqa	.LC12(%rip), %ymm2
	vpermi2q	%ymm1, %ymm3, %ymm2
	vpblendd	$12, %ymm0, %ymm2, %ymm2
	vmovdqa	%ymm2, 32(%rcx)
	vmovdqa	.LC13(%rip), %ymm2
	vpermi2q	%ymm3, %ymm1, %ymm2
	vmovdqa	.LC14(%rip), %ymm1
	vpermt2q	%ymm2, %ymm1, %ymm0
	vmovdqa	%ymm0, 64(%rcx)
	cmpl	%edi, %eax
	je	.L1398
.L1399:
	leal	(%r8,%rdx), %eax
	cltq
	movq	128(%rsp,%rax,8), %rax
	movq	%rax, %rcx
	shrx	%r8, %rax, %rax
	andq	%rbx, %rcx
	shlx	%r8, %rcx, %rcx
	orq	%rax, %rcx
	movslq	%edx, %rax
	movq	128(%rsp,%rax,8), %rax
	movq	%rcx, %rdi
	vmovq	%rcx, %xmm7
	movq	%rax, %rsi
	shrx	%r8, %rax, %rax
	andq	%rbx, %rsi
	shlx	%r8, %rsi, %rsi
	orq	%rax, %rsi
	leal	(%rdx,%rdx,2), %eax
	xorq	%rsi, %rdi
	movslq	%eax, %rcx
	vpinsrq	$1, %rdi, %xmm7, %xmm0
	vmovdqu	%xmm0, 448(%rsp,%rcx,8)
	leal	2(%rax), %ecx
	movslq	%ecx, %rcx
	movq	%rsi, 448(%rsp,%rcx,8)
	leal	1(%rdx), %esi
	cmpl	%esi, %r8d
	jle	.L1398
	leal	(%r8,%rsi), %ecx
	movslq	%esi, %rsi
	addl	$2, %edx
	movslq	%ecx, %rcx
	movq	128(%rsp,%rcx,8), %rdi
	movq	%rbx, %rcx
	andq	%rdi, %rcx
	shrx	%r8, %rdi, %rdi
	shlx	%r8, %rcx, %rcx
	orq	%rdi, %rcx
	movq	128(%rsp,%rsi,8), %rdi
	movq	%rbx, %rsi
	vmovq	%rcx, %xmm7
	andq	%rdi, %rsi
	shrx	%r8, %rdi, %rdi
	shlx	%r8, %rsi, %rsi
	orq	%rdi, %rsi
	movq	%rsi, %rdi
	xorq	%rcx, %rdi
	leal	3(%rax), %ecx
	movslq	%ecx, %rcx
	vpinsrq	$1, %rdi, %xmm7, %xmm0
	vmovdqu	%xmm0, 448(%rsp,%rcx,8)
	leal	5(%rax), %ecx
	movslq	%ecx, %rcx
	movq	%rsi, 448(%rsp,%rcx,8)
	cmpl	%edx, %r8d
	jle	.L1398
	leal	(%r8,%rdx), %ecx
	movslq	%edx, %rdx
	movq	128(%rsp,%rdx,8), %rdx
	movslq	%ecx, %rcx
	movq	128(%rsp,%rcx,8), %rsi
	movq	%rbx, %rcx
	andq	%rdx, %rbx
	shrx	%r8, %rdx, %rdx
	andq	%rsi, %rcx
	shlx	%r8, %rbx, %rbx
	shrx	%r8, %rsi, %rsi
	orq	%rdx, %rbx
	shlx	%r8, %rcx, %rcx
	orq	%rsi, %rcx
	movq	%rbx, %rdx
	xorq	%rcx, %rdx
	vmovq	%rcx, %xmm6
	vpinsrq	$1, %rdx, %xmm6, %xmm0
	leal	6(%rax), %edx
	addl	$8, %eax
	movslq	%edx, %rdx
	cltq
	vmovdqu	%xmm0, 448(%rsp,%rdx,8)
	movq	%rbx, 448(%rsp,%rax,8)
.L1398:
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 16(%r12)
	movq	$0, 56(%rsp)
	vmovdqu	%xmm0, (%r12)
	vzeroupper
	.p2align 4
	.p2align 3
.L1397:
	movq	56(%rsp), %rcx
	movl	$2863311531, %edi
	movq	(%r15,%rcx,8), %r14
	movl	%ecx, %r13d
	movl	%ecx, %ebx
	imulq	%rdi, %r13
	shrx	%r8, %r14, %rax
	shrq	$33, %r13
	orq	%r14, %rax
	bzhi	%r8, %rax, %rax
	popcntq	%rax, %rax
	cmpl	$2, %eax
	jg	.L1401
	movq	80(%rsp), %rdx
	movq	%rdx, 96(%rsp)
	movl	88(%rsp), %edx
	movl	%edx, 104(%rsp)
	leal	0(%r13,%r13,2), %edx
	subl	%edx, %ecx
	cmpl	$2, %ecx
	je	.L1420
	movl	$1, %edx
	shlx	%r13, %rdx, %rdx
	testl	%ecx, %ecx
	jne	.L1402
.L1403:
	movq	8(%r12), %rsi
	movq	%rdx, 112(%rsp)
	movl	%eax, 120(%rsp)
	cmpq	16(%r12), %rsi
	je	.L1404
	vmovdqa	96(%rsp), %xmm5
	addq	$32, %rsi
	vmovdqu	%xmm5, -32(%rsi)
	vmovdqa	112(%rsp), %xmm4
	vmovdqu	%xmm4, -16(%rsi)
	movq	%rsi, 8(%r12)
.L1405:
	movl	nq(%rip), %r8d
.L1401:
	leal	1(%r13), %eax
	leal	3(%r13,%r13,2), %edx
	cmpl	%r8d, %eax
	jge	.L1406
	movl	%ebx, %eax
	movl	$2863311531, %edi
	imulq	%rdi, %rax
	shrq	$33, %rax
	movq	%rax, 72(%rsp)
	movl	72(%rsp), %eax
	leal	(%rax,%rax,2), %eax
	subl	%eax, %ebx
	movl	$1, %eax
	shlx	%r13, %rax, %rcx
	xorl	%eax, %eax
	cmpl	$2, %ebx
	movl	%ebx, 72(%rsp)
	cmovne	%rcx, %rax
	movq	%rcx, 64(%rsp)
	movslq	%edx, %rbx
	movq	%rax, 48(%rsp)
	jmp	.L1413
	.p2align 4
	.p2align 3
.L1441:
	movl	$1, %edi
	shlx	%rdx, %rdi, %rdi
	cmpl	$1, %ecx
	je	.L1409
.L1410:
	xorq	%rdi, %rsi
	movl	%eax, 120(%rsp)
	movq	%rsi, 112(%rsp)
	movq	8(%r12), %rsi
	cmpq	16(%r12), %rsi
	je	.L1411
	vmovdqa	96(%rsp), %xmm7
	addq	$32, %rsi
	vmovdqu	%xmm7, -32(%rsi)
	vmovdqa	112(%rsp), %xmm6
	vmovdqu	%xmm6, -16(%rsi)
	movq	%rsi, 8(%r12)
.L1412:
	movl	nq(%rip), %r8d
.L1407:
	leal	(%r8,%r8,2), %eax
	incq	%rbx
	cmpl	%ebx, %eax
	jle	.L1414
.L1413:
	movq	(%r15,%rbx,8), %rdx
	movl	%ebx, %ecx
	xorq	%r14, %rdx
	shrx	%r8, %rdx, %rax
	orq	%rdx, %rax
	bzhi	%r8, %rax, %rax
	popcntq	%rax, %rax
	cmpl	$2, %eax
	jg	.L1407
	movq	80(%rsp), %rdx
	movq	64(%rsp), %rsi
	movq	%rdx, 96(%rsp)
	movl	88(%rsp), %edx
	movl	%edx, 104(%rsp)
	movl	72(%rsp), %edx
	testl	%edx, %edx
	je	.L1408
	movq	48(%rsp), %rsi
	leal	(%r8,%r13), %edx
	btsq	%rdx, %rsi
.L1408:
	movslq	%ecx, %rdx
	movl	%ecx, %edi
	imulq	$1431655766, %rdx, %rdx
	sarl	$31, %edi
	shrq	$32, %rdx
	subl	%edi, %edx
	leal	(%rdx,%rdx,2), %edi
	subl	%edi, %ecx
	cmpl	$2, %ecx
	jne	.L1441
	xorl	%edi, %edi
.L1409:
	addl	%r8d, %edx
	movl	$1, %ecx
	shlx	%rdx, %rcx, %rdx
	orq	%rdx, %rdi
	jmp	.L1410
	.p2align 4
	.p2align 3
.L1406:
	leal	(%r8,%r8,2), %eax
	.p2align 4
	.p2align 3
.L1414:
	incq	56(%rsp)
	movq	56(%rsp), %rbx
	cmpl	%ebx, %eax
	jg	.L1397
.L1393:
	movq	952(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1442
	leaq	-40(%rbp), %rsp
	movq	%r12, %rax
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
.L1411:
	.cfi_restore_state
	leaq	96(%rsp), %rdx
	movq	%r12, %rdi
.LEHB56:
	call	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
	jmp	.L1412
	.p2align 4
	.p2align 3
.L1420:
	xorl	%edx, %edx
.L1402:
	addl	%r13d, %r8d
	movl	$1, %ecx
	shlx	%r8, %rcx, %rcx
	orq	%rcx, %rdx
	jmp	.L1403
.L1404:
	leaq	96(%rsp), %rdx
	movq	%r12, %rdi
	call	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
.LEHE56:
	jmp	.L1405
.L1394:
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 16(%r12)
	vmovdqu	%xmm0, (%r12)
	jmp	.L1393
.L1419:
	xorl	%eax, %eax
	xorl	%edx, %edx
	jmp	.L1395
.L1442:
	call	__stack_chk_fail@PLT
.L1423:
	endbr64
	movq	%rax, %r13
	jmp	.L1416
	.section	.gcc_except_table
.LLSDA5723:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSE5723-.LLSDACSB5723
.LLSDACSB5723:
	.uleb128 .LEHB56-.LFB5723
	.uleb128 .LEHE56-.LEHB56
	.uleb128 .L1423-.LFB5723
	.uleb128 0
.LLSDACSE5723:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC5723
	.type	_Z13getviolationsRK7CircuitSt5arrayIiLm3EE.cold, @function
_Z13getviolationsRK7CircuitSt5arrayIiLm3EE.cold:
.LFSB5723:
.L1416:
	.cfi_def_cfa 6, 16
	.cfi_offset 3, -56
	.cfi_offset 6, -16
	.cfi_offset 12, -48
	.cfi_offset 13, -40
	.cfi_offset 14, -32
	.cfi_offset 15, -24
	movq	(%r12), %rdi
	movq	16(%r12), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L1439
	vzeroupper
	call	_ZdlPvm@PLT
.L1417:
	movq	%r13, %rdi
.LEHB57:
	call	_Unwind_Resume@PLT
.LEHE57:
.L1439:
	vzeroupper
	jmp	.L1417
	.cfi_endproc
.LFE5723:
	.section	.gcc_except_table
.LLSDAC5723:
	.byte	0xff
	.byte	0xff
	.byte	0x1
	.uleb128 .LLSDACSEC5723-.LLSDACSBC5723
.LLSDACSBC5723:
	.uleb128 .LEHB57-.LCOLDB70
	.uleb128 .LEHE57-.LEHB57
	.uleb128 0
	.uleb128 0
.LLSDACSEC5723:
	.section	.text.unlikely
	.text
	.size	_Z13getviolationsRK7CircuitSt5arrayIiLm3EE, .-_Z13getviolationsRK7CircuitSt5arrayIiLm3EE
	.section	.text.unlikely
	.size	_Z13getviolationsRK7CircuitSt5arrayIiLm3EE.cold, .-_Z13getviolationsRK7CircuitSt5arrayIiLm3EE.cold
.LCOLDE70:
	.text
.LHOTE70:
	.section	.text.unlikely
.LCOLDB73:
	.text
.LHOTB73:
	.p2align 4
	.globl	_Z5sweepRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE
	.type	_Z5sweepRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE, @function
_Z5sweepRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE:
.LFB5743:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA5743
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	vpxor	%xmm0, %xmm0, %xmm0
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
	movq	%rsi, %r15
	andq	$-32, %rsp
	subq	$704, %rsp
	movq	8(%rsi), %rcx
	movq	%rdx, 8(%rsp)
	movq	%fs:40, %rax
	movq	%rax, 696(%rsp)
	xorl	%eax, %eax
	leaq	32(%rdi), %rax
	vmovdqu	%xmm0, (%rdi)
	movq	$0, 16(%rdi)
	movl	$100, 24(%rdi)
	movq	%rax, 40(%rsp)
	vmovdqu	%xmm0, 32(%rdi)
	movq	$0, 48(%rdi)
	movq	(%rsi), %rax
	cmpq	%rcx, %rax
	je	.L1497
	xorl	%esi, %esi
.L1445:
	movq	88(%rax), %rdx
	subq	80(%rax), %rdx
	addq	$104, %rax
	sarq	$3, %rdx
	addl	%edx, %esi
	cmpq	%rax, %rcx
	jne	.L1445
	movl	%esi, 56(%rsp)
.L1444:
	movq	.LC71(%rip), %rax
	movq	$-1, %rdx
	movl	$4294967295, %ecx
	movq	%r15, %rsi
	movl	$-1, 120(%rsp)
	movq	%rax, 112(%rsp)
	leaq	80(%rsp), %rax
	movq	%rax, %rdi
	movq	%rax, 48(%rsp)
.LEHB58:
	call	_Z13getviolationsRK7CircuitSt5arrayIiLm3EE
.LEHE58:
	movq	88(%rsp), %r13
	movq	80(%rsp), %rdi
	incq	(%r12)
	cmpq	%rdi, %r13
	je	.L1446
	movq	8(%r12), %rax
	movq	%rdi, %rbx
	incq	%rax
	vmovq	%rax, %xmm0
	movq	%r13, %rax
	subq	%rdi, %rax
	sarq	$5, %rax
	addq	16(%r12), %rax
	vpinsrq	$1, %rax, %xmm0, %xmm0
	vmovdqu	%xmm0, 8(%r12)
	jmp	.L1449
.L1549:
	vmovdqu	(%rbx), %xmm3
	addq	$32, %rsi
	addq	$32, %rbx
	vmovdqu	%xmm3, -32(%rsi)
	vmovdqu	-16(%rbx), %xmm3
	vmovdqu	%xmm3, -16(%rsi)
	movq	%rsi, 40(%r12)
	cmpq	%rbx, %r13
	je	.L1548
.L1449:
	vmovd	24(%r12), %xmm0
	vmovd	24(%rbx), %xmm1
	vpminsd	%xmm1, %xmm0, %xmm0
	movq	40(%r12), %rsi
	vmovd	%xmm0, 24(%r12)
	cmpq	48(%r12), %rsi
	jne	.L1549
	movq	40(%rsp), %rdi
	movq	%rbx, %rdx
.LEHB59:
	call	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
.LEHE59:
	addq	$32, %rbx
	cmpq	%rbx, %r13
	jne	.L1449
.L1548:
	movq	80(%rsp), %rdi
.L1446:
	testq	%rdi, %rdi
	je	.L1450
	movq	96(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L1450:
	movl	56(%rsp), %eax
	movl	$0, 24(%rsp)
	testl	%eax, %eax
	jle	.L1452
.L1451:
	movl	24(%rsp), %eax
	movq	$-1, 164(%rsp)
	movq	48(%rsp), %rdi
	movq	%r15, %rsi
	movl	168(%rsp), %ecx
	movl	%eax, 160(%rsp)
	movq	160(%rsp), %rdx
.LEHB60:
	call	_Z13getviolationsRK7CircuitSt5arrayIiLm3EE
.LEHE60:
	movq	88(%rsp), %r13
	movq	80(%rsp), %rdi
	incq	(%r12)
	cmpq	%rdi, %r13
	je	.L1456
	movq	8(%r12), %rax
	movq	%rdi, %rbx
	incq	%rax
	vmovq	%rax, %xmm0
	movq	%r13, %rax
	subq	%rdi, %rax
	sarq	$5, %rax
	addq	16(%r12), %rax
	vpinsrq	$1, %rax, %xmm0, %xmm0
	vmovdqu	%xmm0, 8(%r12)
	jmp	.L1459
	.p2align 4
	.p2align 3
.L1551:
	vmovdqu	(%rbx), %xmm3
	addq	$32, %rsi
	addq	$32, %rbx
	vmovdqu	%xmm3, -32(%rsi)
	vmovdqu	-16(%rbx), %xmm3
	vmovdqu	%xmm3, -16(%rsi)
	movq	%rsi, 40(%r12)
	cmpq	%rbx, %r13
	je	.L1550
.L1459:
	vmovd	24(%r12), %xmm0
	vmovd	24(%rbx), %xmm1
	vpminsd	%xmm1, %xmm0, %xmm0
	movq	40(%r12), %rsi
	vmovd	%xmm0, 24(%r12)
	cmpq	48(%r12), %rsi
	jne	.L1551
	movq	40(%rsp), %rdi
	movq	%rbx, %rdx
.LEHB61:
	call	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
.LEHE61:
	addq	$32, %rbx
	cmpq	%rbx, %r13
	jne	.L1459
.L1550:
	movq	80(%rsp), %rdi
.L1456:
	testq	%rdi, %rdi
	je	.L1460
	movq	96(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L1460:
	movl	24(%rsp), %eax
	incl	%eax
	movl	%eax, 20(%rsp)
	cmpl	56(%rsp), %eax
	je	.L1452
	movl	%eax, 28(%rsp)
	.p2align 4
	.p2align 3
.L1461:
	vmovd	24(%rsp), %xmm3
	movl	$4294967295, %ecx
	movq	%r15, %rsi
	movl	$-1, 136(%rsp)
	vpinsrd	$1, 28(%rsp), %xmm3, %xmm2
	movq	48(%rsp), %rdi
	vmovq	%xmm2, %rdx
	vmovq	%xmm2, 32(%rsp)
	vmovq	%xmm2, 128(%rsp)
.LEHB62:
	call	_Z13getviolationsRK7CircuitSt5arrayIiLm3EE
.LEHE62:
	movq	88(%rsp), %r13
	movq	80(%rsp), %rdi
	incq	(%r12)
	cmpq	%rdi, %r13
	je	.L1464
	movq	8(%r12), %rax
	movq	%rdi, %rbx
	incq	%rax
	vmovq	%rax, %xmm0
	movq	%r13, %rax
	subq	%rdi, %rax
	sarq	$5, %rax
	addq	16(%r12), %rax
	vpinsrq	$1, %rax, %xmm0, %xmm0
	vmovdqu	%xmm0, 8(%r12)
	jmp	.L1467
	.p2align 4
	.p2align 3
.L1553:
	vmovdqu	(%rbx), %xmm7
	addq	$32, %rsi
	addq	$32, %rbx
	vmovdqu	%xmm7, -32(%rsi)
	vmovdqu	-16(%rbx), %xmm4
	vmovdqu	%xmm4, -16(%rsi)
	movq	%rsi, 40(%r12)
	cmpq	%rbx, %r13
	je	.L1552
.L1467:
	vmovd	24(%r12), %xmm0
	vmovd	24(%rbx), %xmm1
	vpminsd	%xmm1, %xmm0, %xmm0
	movq	40(%r12), %rsi
	vmovd	%xmm0, 24(%r12)
	cmpq	48(%r12), %rsi
	jne	.L1553
	movq	40(%rsp), %rdi
	movq	%rbx, %rdx
.LEHB63:
	call	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
.LEHE63:
	addq	$32, %rbx
	cmpq	%rbx, %r13
	jne	.L1467
	.p2align 4
	.p2align 3
.L1552:
	movq	80(%rsp), %rdi
.L1464:
	testq	%rdi, %rdi
	je	.L1468
	movq	96(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	incl	28(%rsp)
	movl	28(%rsp), %eax
	cmpl	56(%rsp), %eax
	je	.L1470
.L1469:
	movl	28(%rsp), %r14d
	.p2align 4
	.p2align 3
.L1480:
	movq	32(%rsp), %rax
	movq	48(%rsp), %rdi
	movl	%r14d, %ecx
	movq	%r15, %rsi
	movl	%r14d, 152(%rsp)
	movq	%rax, %rdx
	movq	%rax, 144(%rsp)
.LEHB64:
	call	_Z13getviolationsRK7CircuitSt5arrayIiLm3EE
.LEHE64:
	movq	88(%rsp), %r13
	movq	80(%rsp), %rdi
	incq	(%r12)
	cmpq	%rdi, %r13
	je	.L1473
	movq	8(%r12), %rax
	movq	%rdi, %rbx
	incq	%rax
	vmovq	%rax, %xmm0
	movq	%r13, %rax
	subq	%rdi, %rax
	sarq	$5, %rax
	addq	16(%r12), %rax
	vpinsrq	$1, %rax, %xmm0, %xmm0
	vmovdqu	%xmm0, 8(%r12)
	jmp	.L1476
	.p2align 4
	.p2align 3
.L1555:
	vmovdqu	(%rbx), %xmm5
	addq	$32, %rsi
	addq	$32, %rbx
	vmovdqu	%xmm5, -32(%rsi)
	vmovdqu	-16(%rbx), %xmm6
	vmovdqu	%xmm6, -16(%rsi)
	movq	%rsi, 40(%r12)
	cmpq	%rbx, %r13
	je	.L1554
.L1476:
	vmovd	24(%r12), %xmm0
	vmovd	24(%rbx), %xmm1
	vpminsd	%xmm1, %xmm0, %xmm0
	movq	40(%r12), %rsi
	vmovd	%xmm0, 24(%r12)
	cmpq	48(%r12), %rsi
	jne	.L1555
	movq	40(%rsp), %rdi
	movq	%rbx, %rdx
.LEHB65:
	call	_ZNSt6vectorI10ConstraintSaIS0_EE17_M_realloc_insertIJRKS0_EEEvN9__gnu_cxx17__normal_iteratorIPS0_S2_EEDpOT_
.LEHE65:
	addq	$32, %rbx
	cmpq	%rbx, %r13
	jne	.L1476
	.p2align 4
	.p2align 3
.L1554:
	movq	80(%rsp), %rdi
.L1473:
	testq	%rdi, %rdi
	je	.L1477
	movq	96(%rsp), %rsi
	incl	%r14d
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	cmpl	56(%rsp), %r14d
	jne	.L1480
	jmp	.L1461
	.p2align 4
	.p2align 3
.L1477:
	incl	%r14d
	cmpl	56(%rsp), %r14d
	jne	.L1480
	jmp	.L1461
.L1468:
	incl	28(%rsp)
	movl	28(%rsp), %eax
	cmpl	56(%rsp), %eax
	jne	.L1469
.L1470:
	movl	20(%rsp), %eax
	movl	%eax, 24(%rsp)
	jmp	.L1451
.L1452:
	movq	8(%rsp), %rax
	cmpq	$0, 8(%rax)
	jne	.L1556
.L1443:
	movq	696(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1557
	leaq	-40(%rbp), %rsp
	movq	%r12, %rax
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
.L1556:
	.cfi_restore_state
	leaq	408(%rsp), %r14
	leaq	160(%rsp), %r15
	movq	%r14, %rdi
	call	_ZNSt8ios_baseC2Ev@PLT
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movw	$0, 632(%rsp)
	movq	%rax, 408(%rsp)
	movq	8+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	vmovdqa	%ymm0, 640(%rsp)
	xorl	%esi, %esi
	movq	$0, 624(%rsp)
	movq	-24(%rax), %rdi
	movq	%rax, 160(%rsp)
	movq	16+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	addq	%r15, %rdi
	movq	%rax, (%rdi)
	vzeroupper
.LEHB66:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE4initEPSt15basic_streambufIcS1_E@PLT
.LEHE66:
	leaq	24+_ZTVSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	leaq	168(%rsp), %r13
	movq	%rax, 160(%rsp)
	movq	%r13, %rdi
	addq	$40, %rax
	movq	%rax, 408(%rsp)
.LEHB67:
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEEC1Ev@PLT
.LEHE67:
	movq	%r13, %rsi
	movq	%r14, %rdi
.LEHB68:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE4initEPSt15basic_streambufIcS1_E@PLT
	movq	8(%rsp), %rax
	movl	$16, %edx
	movq	%r13, %rdi
	movq	(%rax), %rsi
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEE4openEPKcSt13_Ios_Openmode@PLT
	movq	160(%rsp), %rdx
	movq	-24(%rdx), %rdi
	addq	%r15, %rdi
	testq	%rax, %rax
	je	.L1558
	xorl	%esi, %esi
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE5clearESt12_Ios_Iostate@PLT
.LEHE68:
.L1485:
	movq	40(%r12), %rax
	movq	32(%r12), %rbx
	leaq	76(%rsp), %rdx
	movq	%rdx, 40(%rsp)
	movq	%rax, 56(%rsp)
	cmpq	%rbx, %rax
	je	.L1492
.L1491:
	movl	(%rbx), %esi
	movq	%r15, %rdi
.LEHB69:
	call	_ZNSolsEi@PLT
	movq	40(%rsp), %rsi
	movq	%rax, %rdi
	movl	$1, %edx
	movb	$32, 76(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movl	4(%rbx), %esi
	movq	%rax, %rdi
	call	_ZNSolsEi@PLT
	movq	%rax, %rdi
	leaq	77(%rsp), %rsi
	movl	$1, %edx
	movb	$32, 77(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movl	8(%rbx), %esi
	movq	%rax, %rdi
	call	_ZNSolsEi@PLT
	movq	%rax, %rdi
	leaq	78(%rsp), %rsi
	movl	$1, %edx
	movb	$32, 78(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movq	16(%rbx), %rsi
	movq	%rax, %rdi
	call	_ZNSo9_M_insertImEERSoT_@PLT
	movq	%rax, %rdi
	leaq	79(%rsp), %rsi
	movl	$1, %edx
	movb	$32, 79(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
	movl	24(%rbx), %esi
	movq	%rax, %rdi
	call	_ZNSolsEi@PLT
	movq	48(%rsp), %rsi
	movq	%rax, %rdi
	movl	$1, %edx
	movb	$10, 80(%rsp)
	call	_ZSt16__ostream_insertIcSt11char_traitsIcEERSt13basic_ostreamIT_T0_ES6_PKS3_l@PLT
.LEHE69:
	addq	$32, %rbx
	cmpq	%rbx, 56(%rsp)
	jne	.L1491
.L1492:
	vmovq	.LC43(%rip), %xmm4
	leaq	64+_ZTVSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	%r13, %rdi
	movq	%rax, 408(%rsp)
	leaq	16+_ZTVSt13basic_filebufIcSt11char_traitsIcEE(%rip), %rax
	vpinsrq	$1, %rax, %xmm4, %xmm0
	vmovdqa	%xmm0, 160(%rsp)
.LEHB70:
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEE5closeEv@PLT
.LEHE70:
.L1487:
	leaq	272(%rsp), %rdi
	call	_ZNSt12__basic_fileIcED1Ev@PLT
	leaq	16+_ZTVSt15basic_streambufIcSt11char_traitsIcEE(%rip), %rax
	leaq	224(%rsp), %rdi
	movq	%rax, 168(%rsp)
	call	_ZNSt6localeD1Ev@PLT
	movq	8+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	%r14, %rdi
	movq	16+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rdx
	movq	%rax, 160(%rsp)
	movq	-24(%rax), %rax
	movq	%rdx, 160(%rsp,%rax)
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	movq	%rax, 408(%rsp)
	call	_ZNSt8ios_baseD2Ev@PLT
	jmp	.L1443
.L1558:
	movl	32(%rdi), %esi
	orl	$4, %esi
.LEHB71:
	call	_ZNSt9basic_iosIcSt11char_traitsIcEE5clearESt12_Ios_Iostate@PLT
.LEHE71:
	jmp	.L1485
.L1497:
	movl	$0, 56(%rsp)
	jmp	.L1444
.L1557:
	call	__stack_chk_fail@PLT
.L1505:
	endbr64
	movq	%rax, %r13
	jmp	.L1481
.L1504:
	endbr64
	movq	%rax, %r13
	jmp	.L1481
.L1503:
	endbr64
	movq	%rax, %r13
	jmp	.L1481
.L1502:
	endbr64
	movq	%rax, %r13
	jmp	.L1481
.L1507:
	endbr64
	movq	%rax, %r13
	vzeroupper
	jmp	.L1489
.L1508:
	endbr64
	movq	%rax, %rbx
	jmp	.L1488
.L1501:
	endbr64
	movq	%rax, %r13
	jmp	.L1494
.L1509:
	endbr64
	movq	%rax, %rdi
	jmp	.L1493
.L1500:
	endbr64
	movq	%rax, %r13
	vzeroupper
	jmp	.L1455
.L1506:
	endbr64
	movq	%rax, %r13
	vzeroupper
	jmp	.L1490
	.section	.gcc_except_table
	.align 4
.LLSDA5743:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATT5743-.LLSDATTD5743
.LLSDATTD5743:
	.byte	0x1
	.uleb128 .LLSDACSE5743-.LLSDACSB5743
.LLSDACSB5743:
	.uleb128 .LEHB58-.LFB5743
	.uleb128 .LEHE58-.LEHB58
	.uleb128 .L1500-.LFB5743
	.uleb128 0
	.uleb128 .LEHB59-.LFB5743
	.uleb128 .LEHE59-.LEHB59
	.uleb128 .L1502-.LFB5743
	.uleb128 0
	.uleb128 .LEHB60-.LFB5743
	.uleb128 .LEHE60-.LEHB60
	.uleb128 .L1500-.LFB5743
	.uleb128 0
	.uleb128 .LEHB61-.LFB5743
	.uleb128 .LEHE61-.LEHB61
	.uleb128 .L1503-.LFB5743
	.uleb128 0
	.uleb128 .LEHB62-.LFB5743
	.uleb128 .LEHE62-.LEHB62
	.uleb128 .L1500-.LFB5743
	.uleb128 0
	.uleb128 .LEHB63-.LFB5743
	.uleb128 .LEHE63-.LEHB63
	.uleb128 .L1504-.LFB5743
	.uleb128 0
	.uleb128 .LEHB64-.LFB5743
	.uleb128 .LEHE64-.LEHB64
	.uleb128 .L1500-.LFB5743
	.uleb128 0
	.uleb128 .LEHB65-.LFB5743
	.uleb128 .LEHE65-.LEHB65
	.uleb128 .L1505-.LFB5743
	.uleb128 0
	.uleb128 .LEHB66-.LFB5743
	.uleb128 .LEHE66-.LEHB66
	.uleb128 .L1506-.LFB5743
	.uleb128 0
	.uleb128 .LEHB67-.LFB5743
	.uleb128 .LEHE67-.LEHB67
	.uleb128 .L1507-.LFB5743
	.uleb128 0
	.uleb128 .LEHB68-.LFB5743
	.uleb128 .LEHE68-.LEHB68
	.uleb128 .L1508-.LFB5743
	.uleb128 0
	.uleb128 .LEHB69-.LFB5743
	.uleb128 .LEHE69-.LEHB69
	.uleb128 .L1501-.LFB5743
	.uleb128 0
	.uleb128 .LEHB70-.LFB5743
	.uleb128 .LEHE70-.LEHB70
	.uleb128 .L1509-.LFB5743
	.uleb128 0x1
	.uleb128 .LEHB71-.LFB5743
	.uleb128 .LEHE71-.LEHB71
	.uleb128 .L1508-.LFB5743
	.uleb128 0
.LLSDACSE5743:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATT5743:
	.text
	.cfi_endproc
	.section	.text.unlikely
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDAC5743
	.type	_Z5sweepRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold, @function
_Z5sweepRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold:
.LFSB5743:
.L1481:
	.cfi_def_cfa 6, 16
	.cfi_offset 3, -56
	.cfi_offset 6, -16
	.cfi_offset 12, -48
	.cfi_offset 13, -40
	.cfi_offset 14, -32
	.cfi_offset 15, -24
	movq	80(%rsp), %rdi
	movq	96(%rsp), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L1542
	vzeroupper
	call	_ZdlPvm@PLT
	jmp	.L1455
.L1488:
	movq	%r13, %rdi
	vzeroupper
	call	_ZNSt13basic_filebufIcSt11char_traitsIcEED1Ev@PLT
	movq	%rbx, %r13
.L1489:
	movq	8+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rax
	movq	16+_ZTTSt14basic_ofstreamIcSt11char_traitsIcEE(%rip), %rdx
	movq	%rax, 160(%rsp)
	movq	-24(%rax), %rax
	movq	%rdx, 160(%rsp,%rax)
.L1490:
	leaq	16+_ZTVSt9basic_iosIcSt11char_traitsIcEE(%rip), %rax
	movq	%r14, %rdi
	movq	%rax, 408(%rsp)
	call	_ZNSt8ios_baseD2Ev@PLT
.L1455:
	movq	32(%r12), %rdi
	movq	48(%r12), %rsi
	subq	%rdi, %rsi
	testq	%rdi, %rdi
	je	.L1495
	call	_ZdlPvm@PLT
.L1495:
	movq	%r13, %rdi
.LEHB72:
	call	_Unwind_Resume@PLT
.LEHE72:
.L1494:
	movq	%r15, %rdi
	vzeroupper
	call	_ZNSt14basic_ofstreamIcSt11char_traitsIcEED1Ev@PLT
	jmp	.L1455
.L1493:
	vzeroupper
	call	__cxa_begin_catch@PLT
	call	__cxa_end_catch@PLT
	jmp	.L1487
.L1542:
	vzeroupper
	jmp	.L1455
	.cfi_endproc
.LFE5743:
	.section	.gcc_except_table
	.align 4
.LLSDAC5743:
	.byte	0xff
	.byte	0x9b
	.uleb128 .LLSDATTC5743-.LLSDATTDC5743
.LLSDATTDC5743:
	.byte	0x1
	.uleb128 .LLSDACSEC5743-.LLSDACSBC5743
.LLSDACSBC5743:
	.uleb128 .LEHB72-.LCOLDB73
	.uleb128 .LEHE72-.LEHB72
	.uleb128 0
	.uleb128 0
.LLSDACSEC5743:
	.byte	0x1
	.byte	0
	.align 4
	.long	0

.LLSDATTC5743:
	.section	.text.unlikely
	.text
	.size	_Z5sweepRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE, .-_Z5sweepRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE
	.section	.text.unlikely
	.size	_Z5sweepRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold, .-_Z5sweepRK7CircuitNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE.cold
.LCOLDE73:
	.text
.LHOTE73:
	.section	.text._ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,"axG",@progbits,_ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_,comdat
	.align 2
	.p2align 4
	.weak	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.type	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, @function
_ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_:
.LFB7123:
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
	movabsq	$-6148914691236517205, %rdx
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rdi), %rbp
	movq	(%rdi), %r13
	movq	%rbp, %rax
	subq	%r13, %rax
	sarq	$2, %rax
	imulq	%rdx, %rax
	movabsq	$768614336404564650, %rdx
	cmpq	%rdx, %rax
	je	.L1580
	testq	%rax, %rax
	movl	$1, %edx
	movq	%rdi, %rbx
	movq	%rsi, %r12
	cmovne	%rax, %rdx
	xorl	%ecx, %ecx
	addq	%rdx, %rax
	movq	%rsi, %rdx
	setc	%cl
	subq	%r13, %rdx
	testq	%rcx, %rcx
	jne	.L1572
	testq	%rax, %rax
	jne	.L1564
	xorl	%r14d, %r14d
	xorl	%edi, %edi
.L1570:
	movq	(%r15), %rax
	subq	%r12, %rbp
	vmovq	%rdi, %xmm1
	movq	%rax, (%rdi,%rdx)
	movl	8(%r15), %eax
	leaq	12(%rdi,%rdx), %r15
	movl	%eax, 8(%rdi,%rdx)
	leaq	(%r15,%rbp), %rax
	vpinsrq	$1, %rax, %xmm1, %xmm0
	vmovdqa	%xmm0, (%rsp)
	testq	%rdx, %rdx
	jg	.L1581
	testq	%rbp, %rbp
	jg	.L1568
	testq	%r13, %r13
	jne	.L1579
.L1569:
	vmovdqa	(%rsp), %xmm2
	movq	%r14, 16(%rbx)
	vmovdqu	%xmm2, (%rbx)
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
.L1581:
	.cfi_restore_state
	movq	%r13, %rsi
	call	memmove@PLT
	testq	%rbp, %rbp
	jg	.L1568
.L1579:
	movq	16(%rbx), %rsi
	movq	%r13, %rdi
	subq	%r13, %rsi
	call	_ZdlPvm@PLT
	jmp	.L1569
	.p2align 4
	.p2align 3
.L1568:
	movq	%rbp, %rdx
	movq	%r12, %rsi
	movq	%r15, %rdi
	call	memcpy@PLT
	testq	%r13, %r13
	je	.L1569
	jmp	.L1579
	.p2align 4
	.p2align 3
.L1572:
	movabsq	$9223372036854775800, %r14
.L1563:
	movq	%r14, %rdi
	movq	%rdx, (%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	(%rsp), %rdx
	addq	%rax, %r14
	jmp	.L1570
	.p2align 4
	.p2align 3
.L1564:
	movabsq	$768614336404564650, %rcx
	cmpq	%rcx, %rax
	cmova	%rcx, %rax
	leaq	(%rax,%rax,2), %r14
	salq	$2, %r14
	jmp	.L1563
.L1580:
	leaq	.LC45(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
	.cfi_endproc
.LFE7123:
	.size	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_, .-_ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	.text
	.p2align 4
	.globl	_Z14orderscenariosi
	.type	_Z14orderscenariosi, @function
_Z14orderscenariosi:
.LFB5781:
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
	subq	$88, %rsp
	.cfi_def_cfa_offset 144
	movq	%fs:40, %rax
	movq	%rax, 72(%rsp)
	xorl	%eax, %eax
	cmpl	%edi, scenario_gates(%rip)
	je	.L1582
	movq	scenarios(%rip), %rsi
	cmpq	8+scenarios(%rip), %rsi
	movl	%edi, %r15d
	movl	%edi, scenario_gates(%rip)
	je	.L1584
	movq	%rsi, 8+scenarios(%rip)
.L1584:
	cmpq	%rsi, 16+scenarios(%rip)
	movl	$-1, 64(%rsp)
	movq	.LC71(%rip), %rax
	movq	%rax, 56(%rsp)
	je	.L1585
	movq	56(%rsp), %rax
	leaq	12(%rsi), %rbp
	movq	%rax, (%rsi)
	movl	64(%rsp), %eax
	movl	%eax, 8(%rsi)
	movq	%rbp, 8+scenarios(%rip)
.L1586:
	testl	%r15d, %r15d
	jle	.L1587
	movq	16+scenarios(%rip), %r12
	xorl	%r14d, %r14d
	movl	%r15d, %r13d
	movl	%r14d, %r15d
.L1593:
	movl	%r15d, 56(%rsp)
	movq	$-1, 60(%rsp)
	cmpq	%rbp, %r12
	je	.L1588
	addq	$12, %rbp
	leal	1(%r15), %r14d
	movq	56(%rsp), %rax
	movl	%r14d, 44(%rsp)
	movq	%rax, -12(%rbp)
	movl	64(%rsp), %eax
	movl	%eax, -4(%rbp)
	movq	%rbp, 8+scenarios(%rip)
	cmpl	%r14d, %r13d
	je	.L1587
.L1625:
	movl	%r13d, %eax
	movl	%r14d, %r13d
	movq	16+scenarios(%rip), %r12
	movl	%eax, %r14d
	.p2align 4
	.p2align 3
.L1605:
	vmovd	%r15d, %xmm2
	movl	$-1, 64(%rsp)
	vpinsrd	$1, %r13d, %xmm2, %xmm0
	vmovq	%xmm0, 56(%rsp)
	cmpq	%rbp, %r12
	je	.L1590
	movq	56(%rsp), %rax
	addq	$12, %rbp
	movq	%rax, -12(%rbp)
	movl	64(%rsp), %eax
	movl	%eax, -4(%rbp)
	leal	1(%r13), %eax
	movq	%rbp, 8+scenarios(%rip)
	movl	%eax, 40(%rsp)
	cmpl	%eax, %r14d
	je	.L1618
.L1591:
	movl	40(%rsp), %ebx
	jmp	.L1604
	.p2align 4
	.p2align 3
.L1621:
	movl	%ebx, 8(%rbp)
	movl	%r15d, 0(%rbp)
	movl	%r13d, 4(%rbp)
	incl	%ebx
	addq	$12, %rbp
	movq	%rbp, 8+scenarios(%rip)
	cmpl	%ebx, %r14d
	je	.L1620
.L1604:
	cmpq	%rbp, %r12
	jne	.L1621
	leaq	scenarios(%rip), %rax
	movq	%r12, %r9
	movq	(%rax), %r8
	movabsq	$-6148914691236517205, %rax
	subq	%r8, %r9
	movq	%r9, %rdx
	sarq	$2, %rdx
	imulq	%rax, %rdx
	movabsq	$768614336404564650, %rax
	cmpq	%rax, %rdx
	je	.L1622
	testq	%rdx, %rdx
	movl	$1, %eax
	cmovne	%rdx, %rax
	addq	%rdx, %rax
	jc	.L1598
	testq	%rax, %rax
	jne	.L1623
	xorl	%ecx, %ecx
	xorl	%edi, %edi
.L1600:
	leaq	(%rdi,%r9), %rax
	leaq	12(%rdi,%r9), %rbp
	vmovq	%rdi, %xmm1
	movl	%r15d, (%rax)
	movl	%r13d, 4(%rax)
	movl	%ebx, 8(%rax)
	vpinsrq	$1, %rbp, %xmm1, %xmm0
	testq	%r9, %r9
	jg	.L1624
	testq	%r8, %r8
	jne	.L1602
.L1603:
	leaq	scenarios(%rip), %rax
	incl	%ebx
	movq	%rcx, 16+scenarios(%rip)
	movq	%rcx, %r12
	vmovdqa	%xmm0, (%rax)
	cmpl	%ebx, %r14d
	jne	.L1604
	.p2align 4
	.p2align 3
.L1620:
	movl	40(%rsp), %r13d
	jmp	.L1605
	.p2align 4
	.p2align 3
.L1624:
	movq	%r8, %rsi
	movq	%r9, %rdx
	vmovdqa	%xmm0, 16(%rsp)
	movq	%rcx, (%rsp)
	movq	%r8, 32(%rsp)
	call	memmove@PLT
	vmovdqa	16(%rsp), %xmm0
	movq	32(%rsp), %r8
	movq	(%rsp), %rcx
.L1602:
	movq	%r12, %rsi
	movq	%r8, %rdi
	vmovdqa	%xmm0, (%rsp)
	movq	%rcx, 32(%rsp)
	subq	%r8, %rsi
	call	_ZdlPvm@PLT
	vmovdqa	(%rsp), %xmm0
	movq	32(%rsp), %rcx
	jmp	.L1603
	.p2align 4
	.p2align 3
.L1590:
	movq	%r12, %rsi
	leaq	56(%rsp), %rdx
	leaq	scenarios(%rip), %rdi
	call	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	leal	1(%r13), %eax
	movq	8+scenarios(%rip), %rbp
	movq	16+scenarios(%rip), %r12
	movl	%eax, 40(%rsp)
	cmpl	%eax, %r14d
	jne	.L1591
	.p2align 4
	.p2align 3
.L1618:
	movl	44(%rsp), %r15d
	movl	%r14d, %r13d
	jmp	.L1593
.L1588:
	movq	%rbp, %rsi
	leaq	56(%rsp), %rdx
	leaq	scenarios(%rip), %rdi
	leal	1(%r15), %r14d
	call	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movq	8+scenarios(%rip), %rbp
	movl	%r14d, 44(%rsp)
	cmpl	%r14d, %r13d
	jne	.L1625
.L1587:
	movq	72(%rsp), %rax
	subq	%fs:40, %rax
	movq	scenarios(%rip), %rdi
	jne	.L1619
	addq	$88, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	movq	%rbp, %rsi
	leaq	rng(%rip), %rdx
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
	jmp	_ZSt7shuffleIN9__gnu_cxx17__normal_iteratorIPSt5arrayIiLm3EESt6vectorIS3_SaIS3_EEEERSt23mersenne_twister_engineImLm64ELm312ELm156ELm31ELm13043109905998158313ELm29ELm6148914691236517205ELm17ELm8202884508482404352ELm37ELm18444473444759240704ELm43ELm6364136223846793005EEEvT_SC_OT0_
.L1582:
	.cfi_restore_state
	movq	72(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1619
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
.L1585:
	.cfi_restore_state
	leaq	56(%rsp), %rdx
	leaq	scenarios(%rip), %rdi
	call	_ZNSt6vectorISt5arrayIiLm3EESaIS1_EE17_M_realloc_insertIJS1_EEEvN9__gnu_cxx17__normal_iteratorIPS1_S3_EEDpOT_
	movq	8+scenarios(%rip), %rbp
	jmp	.L1586
.L1623:
	movabsq	$768614336404564650, %rdx
	cmpq	%rdx, %rax
	cmova	%rdx, %rax
	leaq	(%rax,%rax,2), %rbp
	salq	$2, %rbp
.L1599:
	movq	%rbp, %rdi
	movq	%r9, (%rsp)
	movq	%r8, 32(%rsp)
	call	_Znwm@PLT
	movq	%rax, %rdi
	movq	16+scenarios(%rip), %r12
	movq	32(%rsp), %r8
	leaq	(%rax,%rbp), %rcx
	movq	(%rsp), %r9
	jmp	.L1600
.L1622:
	leaq	.LC45(%rip), %rdi
	call	_ZSt20__throw_length_errorPKc@PLT
.L1598:
	movabsq	$9223372036854775800, %rbp
	jmp	.L1599
.L1619:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE5781:
	.size	_Z14orderscenariosi, .-_Z14orderscenariosi
	.p2align 4
	.globl	_Z10exactscoreRK7Circuitdd
	.type	_Z10exactscoreRK7Circuitdd, @function
_Z10exactscoreRK7Circuitdd:
.LFB5782:
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
	leaq	-57344(%rsp), %r11
.LPSRL0:
	subq	$4096, %rsp
	orq	$0, (%rsp)
	cmpq	%r11, %rsp
	jne	.LPSRL0
	subq	$1792, %rsp
	.cfi_offset 15, -24
	.cfi_offset 14, -32
	.cfi_offset 13, -40
	.cfi_offset 12, -48
	.cfi_offset 3, -56
	movq	(%rsi), %rdx
	movq	8(%rsi), %rcx
	movq	%rdi, 176(%rsp)
	vmovsd	%xmm0, 104(%rsp)
	vmovsd	%xmm1, 96(%rsp)
	movq	%rsi, %r12
	xorl	%edi, %edi
	movq	%fs:40, %rax
	movq	%rax, 59128(%rsp)
	xorl	%eax, %eax
	cmpq	%rcx, %rdx
	je	.L1627
	.p2align 4
	.p2align 3
.L1628:
	movq	88(%rdx), %rax
	subq	80(%rdx), %rax
	addq	$104, %rdx
	sarq	$3, %rax
	addl	%eax, %edi
	cmpq	%rdx, %rcx
	jne	.L1628
.L1627:
	call	_Z14orderscenariosi
	movq	176(%rsp), %rax
	vpxor	%xmm0, %xmm0, %xmm0
	movq	%r12, %rsi
	vmovdqu	%xmm0, (%rax)
	movq	$0x000000000, 16(%rax)
	movb	$1, 24(%rax)
	leaq	1104(%rsp), %rax
	movq	%rax, %rdi
	movq	%rax, 152(%rsp)
	call	_ZN7FastMapC1ERK7Circuit
	movq	8+scenarios(%rip), %rax
	movq	scenarios(%rip), %rcx
	movq	%rax, 72(%rsp)
	cmpq	%rcx, %rax
	je	.L1629
	movl	nq(%rip), %ebx
	movq	%rcx, 200(%rsp)
	movq	$0, 184(%rsp)
	movq	$0, 192(%rsp)
	movq	$-1, %r13
	leaq	256(%rsp), %r8
	vxorps	%xmm13, %xmm13, %xmm13
	leaq	576(%rsp), %r14
	vmovdqa	.LC52(%rip), %ymm12
	vpbroadcastd	.LC57(%rip), %ymm7
	movq	%r8, %r10
	vpbroadcastd	.LC76(%rip), %ymm11
	vmovdqa32	.LC49(%rip), %zmm10
	leal	(%rbx,%rbx), %r12d
	vpbroadcastd	.LC57(%rip), %zmm6
	vpbroadcastd	.LC76(%rip), %zmm9
	shlx	%rbx, %r13, %r13
	movslq	%r12d, %rax
	vmovdqa64	.LC10(%rip), %ymm18
	vmovdqa64	.LC11(%rip), %ymm17
	addl	%ebx, %r12d
	salq	$3, %rax
	vmovdqa64	.LC12(%rip), %ymm16
	vmovdqa	.LC13(%rip), %ymm15
	notq	%r13
	movq	%rax, 112(%rsp)
	movq	1472(%rsp), %rax
	vmovdqa	.LC14(%rip), %ymm14
	vmovdqa64	.LC4(%rip), %zmm24
	movq	%rax, 160(%rsp)
	movq	1496(%rsp), %rax
	movq	%rax, 168(%rsp)
	movq	1424(%rsp), %rax
	movq	%rax, 136(%rsp)
	movq	1448(%rsp), %rax
	movq	%rax, 128(%rsp)
	leal	-1(%rbx), %eax
	movl	%eax, 120(%rsp)
	movl	%ebx, %eax
	shrl	$3, %eax
	movl	%eax, 68(%rsp)
	movslq	%ebx, %rax
	movq	%rax, 144(%rsp)
	leaq	256(%rsp,%rax,8), %rax
	movq	%rax, 56(%rsp)
	movl	%ebx, %eax
	andl	$-8, %eax
	movl	%eax, 64(%rsp)
	leaq	208(%rsp), %rax
	movq	%rax, 88(%rsp)
	leaq	224(%rsp), %rax
	movq	%rax, 80(%rsp)
	vmovdqa64	.LC5(%rip), %zmm23
	vmovdqa64	.LC6(%rip), %zmm22
	vmovdqa64	.LC7(%rip), %zmm21
	vmovdqa64	.LC8(%rip), %zmm20
	vmovdqa64	.LC9(%rip), %zmm19
	.p2align 4
	.p2align 3
.L1673:
	movq	200(%rsp), %rsi
	movq	(%rsi), %rdx
	movl	8(%rsi), %eax
	movq	%rdx, 208(%rsp)
	movq	112(%rsp), %rdx
	movl	%eax, 216(%rsp)
	testq	%rdx, %rdx
	je	.L1630
	movq	152(%rsp), %rsi
	movq	%r10, %rdi
	vzeroupper
	call	memcpy@PLT
	vmovdqa64	.LC9(%rip), %zmm19
	vxorps	%xmm13, %xmm13, %xmm13
	vmovdqa64	.LC8(%rip), %zmm20
	vmovdqa64	.LC7(%rip), %zmm21
	movq	%rax, %r10
	vmovdqa64	.LC6(%rip), %zmm22
	vmovdqa64	.LC5(%rip), %zmm23
	vmovdqa64	.LC4(%rip), %zmm24
	vmovdqa	.LC14(%rip), %ymm14
	vmovdqa	.LC13(%rip), %ymm15
	vmovdqa64	.LC12(%rip), %ymm16
	vmovdqa64	.LC11(%rip), %ymm17
	vmovdqa64	.LC10(%rip), %ymm18
	vmovdqa32	.LC74(%rip), %zmm9
	vmovdqa32	.LC51(%rip), %zmm6
	vmovdqa32	.LC49(%rip), %zmm10
	vmovdqa	.LC75(%rip), %ymm11
	vmovdqa	.LC55(%rip), %ymm7
	vmovdqa	.LC52(%rip), %ymm12
.L1630:
	movq	88(%rsp), %rcx
	movq	80(%rsp), %r9
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 240(%rsp)
	vmovdqa	%xmm0, 224(%rsp)
	vmovdqa	%xmm0, 576(%rsp)
	movq	$0, 592(%rsp)
	movq	%r14, %rsi
	movl	$3, %eax
.L1632:
	movslq	8(%rcx), %r8
	testl	%r8d, %r8d
	js	.L1649
	movq	160(%rsp), %rdi
	movq	168(%rsp), %rdx
	leaq	0(,%r8,8), %r15
	movq	(%rdi,%r15), %rdi
	movq	(%rdx,%r15), %rdx
	cmpl	$3, %eax
	je	.L1634
	movq	152(%rsp), %r11
	imulq	$480, %r8, %r8
	leaq	416(%r11,%r8), %r11
	movslq	12(%rcx), %r8
	vmovq	%r11, %xmm5
	testl	%r8d, %r8d
	js	.L1635
	leaq	(%r11,%r8,4), %r8
	movzbl	1(%r8), %r11d
	cmpb	$0, (%r8)
	movb	%r11b, 127(%rsp)
	movzbl	2(%r8), %r11d
	movb	%r11b, 126(%rsp)
	movzbl	3(%r8), %r11d
	movb	%r11b, 125(%rsp)
	je	.L1641
	xorq	24(%r9), %rdi
.L1641:
	cmpb	$0, 127(%rsp)
	je	.L1640
	xorq	24(%rsi), %rdi
.L1640:
	cmpb	$0, 126(%rsp)
	je	.L1639
	xorq	24(%r9), %rdx
.L1639:
	cmpb	$0, 125(%rsp)
	je	.L1635
	xorq	24(%rsi), %rdx
.L1635:
	cmpl	$2, %eax
	je	.L1634
	movslq	16(%rcx), %r8
	testl	%r8d, %r8d
	js	.L1634
	vmovq	%xmm5, %r11
	leaq	(%r11,%r8,4), %r8
	movzbl	1(%r8), %r11d
	cmpb	$0, (%r8)
	movb	%r11b, 125(%rsp)
	movzbl	2(%r8), %r11d
	movb	%r11b, 126(%rsp)
	movzbl	3(%r8), %r11d
	movb	%r11b, 127(%rsp)
	je	.L1644
	xorq	32(%r9), %rdi
.L1644:
	cmpb	$0, 125(%rsp)
	je	.L1645
	xorq	32(%rsi), %rdi
.L1645:
	cmpb	$0, 126(%rsp)
	je	.L1646
	xorq	32(%r9), %rdx
.L1646:
	cmpb	$0, 127(%rsp)
	je	.L1634
	xorq	32(%rsi), %rdx
	.p2align 4
	.p2align 3
.L1634:
	movq	%rdi, 16(%r9)
	movq	%rdx, 16(%rsi)
	testq	%rdi, %rdi
	je	.L1651
	movq	136(%rsp), %r11
	movq	(%r11,%r15), %r11
	.p2align 4
	.p2align 3
.L1650:
	tzcntq	%rdi, %r8
	xorq	%r11, (%r10,%r8,8)
	blsr	%rdi, %rdi
	jne	.L1650
.L1651:
	testq	%rdx, %rdx
	je	.L1649
	movq	128(%rsp), %rdi
	movq	(%rdi,%r15), %r8
	.p2align 4
	.p2align 3
.L1652:
	tzcntq	%rdx, %rdi
	xorq	%r8, (%r10,%rdi,8)
	blsr	%rdx, %rdx
	jne	.L1652
.L1649:
	subq	$4, %rcx
	subq	$8, %r9
	subq	$8, %rsi
	decl	%eax
	jne	.L1632
	testl	%ebx, %ebx
	jle	.L1653
	cmpl	$6, 120(%rsp)
	jbe	.L1680
	movq	56(%rsp), %rax
	vmovdqa64	256(%rsp), %zmm2
	vmovdqa64	256(%rsp), %zmm3
	cmpl	$1, 68(%rsp)
	vmovdqu64	(%rax), %zmm1
	vpxorq	256(%rsp), %zmm1, %zmm0
	vpermt2q	%zmm0, %zmm24, %zmm2
	vpermt2q	%zmm0, %zmm22, %zmm3
	vpermt2q	256(%rsp), %zmm20, %zmm0
	vpermt2q	%zmm1, %zmm23, %zmm2
	vpermt2q	%zmm1, %zmm19, %zmm0
	vmovdqa64	%zmm2, 576(%rsp)
	vmovdqa64	%zmm1, %zmm2
	vmovdqa64	%zmm0, 704(%rsp)
	vpermt2q	%zmm3, %zmm21, %zmm2
	vmovdqa64	%zmm2, 640(%rsp)
	jbe	.L1655
	vmovdqu64	64(%rax), %zmm1
	vpxorq	320(%rsp), %zmm1, %zmm0
	vmovdqa64	320(%rsp), %zmm2
	vmovdqa64	320(%rsp), %zmm3
	vpermt2q	%zmm0, %zmm24, %zmm2
	vpermt2q	%zmm1, %zmm23, %zmm2
	vpermt2q	%zmm0, %zmm22, %zmm3
	vpermt2q	320(%rsp), %zmm20, %zmm0
	vmovdqa64	%zmm2, 768(%rsp)
	vmovdqa64	%zmm1, %zmm2
	vpermt2q	%zmm1, %zmm19, %zmm0
	vpermt2q	%zmm3, %zmm21, %zmm2
	vmovdqa64	%zmm0, 896(%rsp)
	vmovdqa64	%zmm2, 832(%rsp)
.L1655:
	movl	64(%rsp), %edx
	movl	%edx, %eax
	cmpl	%eax, %ebx
	je	.L1660
.L1654:
	movl	%ebx, %edi
	subl	%eax, %edi
	leal	-1(%rdi), %r8d
	cmpl	$2, %r8d
	jbe	.L1657
	vmovdqa	256(%rsp,%rax,8), %ymm1
	leaq	(%rax,%rax,2), %r8
	addq	144(%rsp), %rax
	leaq	(%r14,%r8,8), %r8
	vmovdqu	256(%rsp,%rax,8), %ymm0
	movl	%edi, %eax
	andl	$-4, %eax
	addl	%eax, %edx
	vmovdqa	%ymm1, %ymm3
	vpxor	%ymm0, %ymm1, %ymm2
	vpermt2q	%ymm2, %ymm18, %ymm3
	vpermt2q	%ymm0, %ymm17, %ymm3
	vmovdqa	%ymm3, (%r8)
	vmovdqa	%ymm2, %ymm3
	vpermt2q	%ymm1, %ymm16, %ymm3
	vpermt2q	%ymm2, %ymm15, %ymm1
	vpblendd	$12, %ymm0, %ymm3, %ymm3
	vpermt2q	%ymm1, %ymm14, %ymm0
	vmovdqa	%ymm3, 32(%r8)
	vmovdqa	%ymm0, 64(%r8)
	cmpl	%eax, %edi
	je	.L1660
.L1657:
	movslq	%edx, %rax
	leal	(%rdx,%rdx,2), %edi
	movq	256(%rsp,%rax,8), %r11
	leal	(%rbx,%rdx), %eax
	cltq
	movq	256(%rsp,%rax,8), %r8
	movq	%r11, %rax
	vmovq	%r11, %xmm5
	xorq	%r8, %rax
	vpinsrq	$1, %rax, %xmm5, %xmm0
	movslq	%edi, %rax
	vmovdqu	%xmm0, (%r14,%rax,8)
	leal	2(%rdi), %eax
	cltq
	movq	%r8, 576(%rsp,%rax,8)
	leal	1(%rdx), %eax
	cmpl	%eax, %ebx
	jle	.L1660
	movslq	%eax, %r8
	addl	%ebx, %eax
	addl	$2, %edx
	movq	256(%rsp,%r8,8), %r11
	cltq
	movq	256(%rsp,%rax,8), %r8
	movq	%r11, %rax
	vmovq	%r11, %xmm5
	xorq	%r8, %rax
	vpinsrq	$1, %rax, %xmm5, %xmm0
	leal	3(%rdi), %eax
	cltq
	vmovdqu	%xmm0, (%r14,%rax,8)
	leal	5(%rdi), %eax
	cltq
	movq	%r8, 576(%rsp,%rax,8)
	cmpl	%edx, %ebx
	jle	.L1660
	movslq	%edx, %rax
	addl	%ebx, %edx
	movq	256(%rsp,%rax,8), %rax
	movslq	%edx, %rdx
	movq	256(%rsp,%rdx,8), %rdx
	movq	%rax, %r8
	vmovq	%rax, %xmm5
	leal	6(%rdi), %eax
	addl	$8, %edi
	xorq	%rdx, %r8
	cltq
	movslq	%edi, %rdi
	vpinsrq	$1, %r8, %xmm5, %xmm0
	vmovdqu	%xmm0, (%r14,%rax,8)
	movq	%rdx, 576(%rsp,%rdi,8)
.L1660:
	xorl	%r11d, %r11d
	xorl	%edx, %edx
	xorl	%eax, %eax
	vpbroadcastq	%r13, %ymm8
	movq	192(%rsp), %r9
	movq	184(%rsp), %rsi
	.p2align 4
	.p2align 3
.L1659:
	movq	(%r14,%r11,8), %rdi
	movl	%r11d, %ecx
	shrx	%rbx, %rdi, %r8
	orq	%rdi, %r8
	andq	%r13, %r8
	popcntq	%r8, %r8
	cmpl	$2, %r8d
	jg	.L1662
	incq	%rsi
	movl	$1, %eax
.L1662:
	movl	$2863311531, %r15d
	imulq	%r15, %rcx
	shrq	$33, %rcx
	leal	3(%rcx,%rcx,2), %r15d
	leal	1(%rcx), %r8d
	movl	%r15d, %ecx
	cmpl	%r12d, %r15d
	jge	.L1663
	movl	%r12d, %eax
	subl	%r15d, %eax
	leal	-1(%rax), %edx
	cmpl	$14, %edx
	jbe	.L1681
	movslq	%r8d, %rcx
	vpbroadcastq	%rdi, %zmm28
	vmovd	%ebx, %xmm0
	vpbroadcastq	%r13, %zmm27
	leaq	(%rcx,%rcx,2), %rcx
	movl	%eax, %edx
	leaq	(%r14,%rcx,8), %rcx
	shrl	$4, %edx
	vpxorq	(%rcx), %zmm28, %zmm26
	vpxorq	64(%rcx), %zmm28, %zmm25
	vpsrlq	%xmm0, %zmm25, %zmm4
	vporq	%zmm25, %zmm4, %zmm4
	vpsrlq	%xmm0, %zmm26, %zmm25
	vporq	%zmm26, %zmm25, %zmm25
	vpandq	%zmm27, %zmm4, %zmm4
	vpandq	%zmm27, %zmm25, %zmm25
	vpopcntq	%zmm4, %zmm4
	vpopcntq	%zmm25, %zmm25
	vpermt2d	%zmm4, %zmm10, %zmm25
	vpcmpd	$2, %zmm6, %zmm25, %k1
	vmovdqa32	%zmm6, %zmm26{%k1}{z}
	vpcmpd	$0, %zmm9, %zmm25, %k1
	vextracti32x8	$0x1, %zmm26, %ymm4
	vpmovzxdq	%ymm26, %zmm26
	vpmovzxdq	%ymm4, %zmm4
	vpaddq	%zmm26, %zmm4, %zmm4
	vmovdqa32	%zmm6, %zmm26{%k1}{z}
	vextracti32x8	$0x1, %zmm26, %ymm25
	vpmovzxdq	%ymm26, %zmm26
	vpmovzxdq	%ymm25, %zmm25
	vpaddq	%zmm26, %zmm25, %zmm25
	cmpl	$1, %edx
	je	.L1665
	vpxorq	128(%rcx), %zmm28, %zmm31
	vpxorq	192(%rcx), %zmm28, %zmm26
	vpsrlq	%xmm0, %zmm26, %zmm30
	vporq	%zmm26, %zmm30, %zmm30
	vpsrlq	%xmm0, %zmm31, %zmm26
	vporq	%zmm31, %zmm26, %zmm26
	vpandq	%zmm27, %zmm30, %zmm30
	vpandq	%zmm27, %zmm26, %zmm26
	vpopcntq	%zmm30, %zmm30
	vpopcntq	%zmm26, %zmm26
	vpermt2d	%zmm30, %zmm10, %zmm26
	vpcmpd	$2, %zmm6, %zmm26, %k1
	vmovdqa32	%zmm6, %zmm31{%k1}{z}
	vpcmpd	$0, %zmm9, %zmm26, %k1
	vmovdqa32	%zmm6, %zmm26{%k1}{z}
	vpmovzxdq	%ymm31, %zmm30
	vpaddq	%zmm4, %zmm30, %zmm30
	vextracti32x8	$0x1, %zmm31, %ymm4
	vpmovzxdq	%ymm4, %zmm4
	vpaddq	%zmm30, %zmm4, %zmm4
	vpmovzxdq	%ymm26, %zmm30
	vextracti32x8	$0x1, %zmm26, %ymm26
	vpaddq	%zmm25, %zmm30, %zmm25
	vpmovzxdq	%ymm26, %zmm26
	vpaddq	%zmm25, %zmm26, %zmm25
	cmpl	$2, %edx
	je	.L1665
	vpxorq	256(%rcx), %zmm28, %zmm30
	vpxorq	320(%rcx), %zmm28, %zmm28
	vpsrlq	%xmm0, %zmm28, %zmm26
	vpsrlq	%xmm0, %zmm30, %zmm0
	vporq	%zmm28, %zmm26, %zmm26
	vporq	%zmm30, %zmm0, %zmm0
	vpandq	%zmm27, %zmm26, %zmm26
	vpandq	%zmm27, %zmm0, %zmm0
	vpopcntq	%zmm26, %zmm26
	vpopcntq	%zmm0, %zmm0
	vpermt2d	%zmm26, %zmm10, %zmm0
	vpcmpd	$2, %zmm6, %zmm0, %k1
	vmovdqa32	%zmm6, %zmm26{%k1}{z}
	vpcmpd	$0, %zmm9, %zmm0, %k1
	vmovdqa32	%zmm6, %zmm0{%k1}{z}
	vpmovzxdq	%ymm26, %zmm27
	vextracti32x8	$0x1, %zmm26, %ymm26
	vpmovzxdq	%ymm26, %zmm26
	vpaddq	%zmm4, %zmm27, %zmm4
	vpaddq	%zmm4, %zmm26, %zmm4
	vpmovzxdq	%ymm0, %zmm26
	vextracti32x8	$0x1, %zmm0, %ymm0
	vpaddq	%zmm25, %zmm26, %zmm25
	vpmovzxdq	%ymm0, %zmm0
	vpaddq	%zmm25, %zmm0, %zmm25
.L1665:
	vextracti64x4	$0x1, %zmm25, %ymm0
	vpaddq	%ymm25, %ymm0, %ymm25
	vextracti64x2	$0x1, %ymm25, %xmm0
	vpaddq	%xmm25, %xmm0, %xmm0
	vpsrldq	$8, %xmm0, %xmm25
	vpaddq	%xmm25, %xmm0, %xmm0
	vmovq	%xmm0, %rdx
	vextracti64x4	$0x1, %zmm4, %ymm0
	vpaddq	%ymm4, %ymm0, %ymm4
	addq	%rdx, %r9
	vextracti64x2	$0x1, %ymm4, %xmm0
	vpaddq	%xmm4, %xmm0, %xmm0
	vpsrldq	$8, %xmm0, %xmm4
	vpaddq	%xmm4, %xmm0, %xmm0
	vmovq	%xmm0, %rdx
	addq	%rdx, %rsi
	movl	%eax, %edx
	andl	$-16, %edx
	leal	(%r15,%rdx), %ecx
	cmpl	%eax, %edx
	je	.L1666
.L1664:
	subl	%edx, %eax
	leal	-1(%rax), %r15d
	cmpl	$6, %r15d
	jbe	.L1667
	movslq	%r8d, %r8
	vpbroadcastq	%rdi, %ymm26
	vmovd	%ebx, %xmm0
	leaq	(%r8,%r8,2), %r8
	addq	%r8, %rdx
	leaq	(%r14,%rdx,8), %rdx
	vpxorq	(%rdx), %ymm26, %ymm27
	vpxorq	32(%rdx), %ymm26, %ymm26
	vpsrlq	%xmm0, %ymm26, %ymm25
	vpsrlq	%xmm0, %ymm27, %ymm0
	vporq	%ymm26, %ymm25, %ymm25
	vporq	%ymm27, %ymm0, %ymm0
	vpandq	%ymm8, %ymm25, %ymm25
	vpand	%ymm8, %ymm0, %ymm0
	vpopcntq	%ymm25, %ymm25
	vpopcntq	%ymm0, %ymm0
	vpermt2d	%ymm25, %ymm12, %ymm0
	vpcmpgtd	%ymm7, %ymm0, %ymm1
	vpcmpeqd	%ymm11, %ymm0, %ymm0
	vpandnd	%ymm7, %ymm1, %ymm26
	vpand	%ymm7, %ymm0, %ymm0
	vpmovzxdq	%xmm26, %ymm25
	vextracti32x4	$0x1, %ymm26, %xmm26
	vpmovzxdq	%xmm26, %ymm26
	vpaddq	%ymm26, %ymm25, %ymm25
	vpmovzxdq	%xmm0, %ymm26
	vextracti128	$0x1, %ymm0, %xmm0
	vpmovzxdq	%xmm0, %ymm0
	vpaddq	%ymm0, %ymm26, %ymm26
	vmovdqa64	%xmm26, %xmm0
	vextracti64x2	$0x1, %ymm26, %xmm26
	vpaddq	%xmm26, %xmm0, %xmm0
	vpsrldq	$8, %xmm0, %xmm26
	vpaddq	%xmm26, %xmm0, %xmm0
	vmovq	%xmm0, %rdx
	vmovdqa64	%xmm25, %xmm0
	vextracti64x2	$0x1, %ymm25, %xmm25
	vpaddq	%xmm25, %xmm0, %xmm0
	addq	%rdx, %r9
	vpsrldq	$8, %xmm0, %xmm25
	vpaddq	%xmm25, %xmm0, %xmm0
	vmovq	%xmm0, %rdx
	addq	%rdx, %rsi
	movl	%eax, %edx
	andl	$-8, %edx
	addl	%edx, %ecx
	cmpl	%eax, %edx
	je	.L1666
.L1667:
	movslq	%ecx, %rax
	movq	576(%rsp,%rax,8), %rdx
	xorq	%rdi, %rdx
	shrx	%rbx, %rdx, %rax
	orq	%rdx, %rax
	xorl	%edx, %edx
	andq	%r13, %rax
	popcntq	%rax, %rax
	cmpl	$1, %eax
	setle	%dl
	addq	%rdx, %rsi
	cmpl	$2, %eax
	sete	%al
	movzbl	%al, %eax
	addq	%rax, %r9
	leal	1(%rcx), %eax
	cmpl	%eax, %r12d
	jle	.L1666
	cltq
	movq	576(%rsp,%rax,8), %rdx
	xorq	%rdi, %rdx
	shrx	%rbx, %rdx, %rax
	orq	%rdx, %rax
	xorl	%edx, %edx
	andq	%r13, %rax
	popcntq	%rax, %rax
	cmpl	$1, %eax
	setle	%dl
	addq	%rdx, %rsi
	cmpl	$2, %eax
	sete	%al
	movzbl	%al, %eax
	addq	%rax, %r9
	leal	2(%rcx), %eax
	cmpl	%r12d, %eax
	jge	.L1666
	cltq
	movq	576(%rsp,%rax,8), %rdx
	xorq	%rdi, %rdx
	shrx	%rbx, %rdx, %rax
	orq	%rdx, %rax
	xorl	%edx, %edx
	andq	%r13, %rax
	popcntq	%rax, %rax
	cmpl	$1, %eax
	setle	%dl
	addq	%rdx, %rsi
	cmpl	$2, %eax
	sete	%al
	movzbl	%al, %eax
	addq	%rax, %r9
	leal	3(%rcx), %eax
	cmpl	%r12d, %eax
	jge	.L1666
	cltq
	movq	576(%rsp,%rax,8), %rdx
	xorq	%rdi, %rdx
	shrx	%rbx, %rdx, %rax
	orq	%rdx, %rax
	xorl	%edx, %edx
	andq	%r13, %rax
	popcntq	%rax, %rax
	cmpl	$1, %eax
	setle	%dl
	addq	%rdx, %rsi
	cmpl	$2, %eax
	sete	%al
	movzbl	%al, %eax
	addq	%rax, %r9
	leal	4(%rcx), %eax
	cmpl	%r12d, %eax
	jge	.L1666
	cltq
	movq	576(%rsp,%rax,8), %rdx
	xorq	%rdi, %rdx
	shrx	%rbx, %rdx, %rax
	orq	%rdx, %rax
	xorl	%edx, %edx
	andq	%r13, %rax
	popcntq	%rax, %rax
	cmpl	$1, %eax
	setle	%dl
	addq	%rdx, %rsi
	cmpl	$2, %eax
	sete	%al
	movzbl	%al, %eax
	addq	%rax, %r9
	leal	5(%rcx), %eax
	cmpl	%r12d, %eax
	jge	.L1666
	cltq
	movq	576(%rsp,%rax,8), %rdx
	xorq	%rdi, %rdx
	shrx	%rbx, %rdx, %rax
	orq	%rdx, %rax
	xorl	%edx, %edx
	andq	%r13, %rax
	popcntq	%rax, %rax
	cmpl	$1, %eax
	setle	%dl
	addq	%rdx, %rsi
	cmpl	$2, %eax
	sete	%al
	addl	$6, %ecx
	movzbl	%al, %eax
	addq	%rax, %r9
	cmpl	%r12d, %ecx
	jge	.L1666
	movslq	%ecx, %rcx
	xorl	%edx, %edx
	xorq	576(%rsp,%rcx,8), %rdi
	shrx	%rbx, %rdi, %rax
	orq	%rdi, %rax
	andq	%r13, %rax
	popcntq	%rax, %rax
	cmpl	$1, %eax
	setle	%dl
	addq	%rdx, %rsi
	cmpl	$2, %eax
	sete	%al
	movzbl	%al, %eax
	addq	%rax, %r9
.L1666:
	movl	$1, %edx
	movl	$1, %eax
.L1663:
	incq	%r11
	cmpl	%r11d, %r12d
	jg	.L1659
	testb	%dl, %dl
	je	.L1669
	movq	176(%rsp), %rdi
	movq	%r9, 192(%rsp)
	movq	%r9, 8(%rdi)
.L1669:
	testb	%al, %al
	je	.L1661
	movq	176(%rsp), %rax
	movq	%rsi, 184(%rsp)
	movq	%rsi, (%rax)
.L1661:
	vcvtsi2sdq	184(%rsp), %xmm13, %xmm0
	vcvtsi2sdq	192(%rsp), %xmm13, %xmm1
	vfmadd132sd	96(%rsp), %xmm1, %xmm0
	movq	176(%rsp), %rax
	vcomisd	104(%rsp), %xmm0
	vmovsd	%xmm0, 16(%rax)
	ja	.L1737
	addq	$12, 200(%rsp)
	movq	200(%rsp), %rax
	cmpq	%rax, 72(%rsp)
	jne	.L1673
	vzeroupper
.L1672:
	movq	168(%rsp), %rax
	testq	%rax, %rax
	je	.L1674
	movq	1512(%rsp), %rsi
	movq	%rax, %rdi
	subq	%rax, %rsi
	call	_ZdlPvm@PLT
.L1674:
	movq	1472(%rsp), %rdi
	testq	%rdi, %rdi
	je	.L1675
	movq	1488(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L1675:
	movq	1448(%rsp), %rdi
	testq	%rdi, %rdi
	je	.L1676
	movq	1464(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L1676:
	movq	1424(%rsp), %rdi
	testq	%rdi, %rdi
	je	.L1626
	movq	1440(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L1626:
	movq	59128(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1738
	movq	176(%rsp), %rax
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
.L1681:
	.cfi_restore_state
	xorl	%edx, %edx
	jmp	.L1664
.L1653:
	testl	%r12d, %r12d
	jle	.L1661
	jmp	.L1660
	.p2align 4
	.p2align 3
.L1680:
	xorl	%eax, %eax
	xorl	%edx, %edx
	jmp	.L1654
.L1737:
	movb	$0, 24(%rax)
	vzeroupper
	jmp	.L1672
.L1629:
	movq	1496(%rsp), %rax
	movq	%rax, 168(%rsp)
	jmp	.L1672
.L1738:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE5782:
	.size	_Z10exactscoreRK7Circuitdd, .-_Z10exactscoreRK7Circuitdd
	.p2align 4
	.globl	_Z13criticalscoreRK7Circuitd
	.type	_Z13criticalscoreRK7Circuitd, @function
_Z13criticalscoreRK7Circuitd:
.LFB5793:
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
	leaq	-57344(%rsp), %r11
	.cfi_def_cfa 11, 57400
.LPSRL1:
	subq	$4096, %rsp
	orq	$0, (%rsp)
	cmpq	%r11, %rsp
	jne	.LPSRL1
	.cfi_def_cfa_register 7
	subq	$1176, %rsp
	.cfi_def_cfa_offset 58576
	movq	(%rdi), %rdx
	movq	8(%rdi), %rcx
	vmovsd	%xmm0, 40(%rsp)
	movq	%rdi, %rbp
	xorl	%edi, %edi
	movq	%fs:40, %rax
	movq	%rax, 58504(%rsp)
	xorl	%eax, %eax
	cmpq	%rcx, %rdx
	je	.L1740
	.p2align 4
	.p2align 3
.L1741:
	movq	88(%rdx), %rax
	subq	80(%rdx), %rax
	addq	$104, %rdx
	sarq	$3, %rax
	addl	%eax, %edi
	cmpq	%rdx, %rcx
	jne	.L1741
.L1740:
	leaq	480(%rsp), %r13
	call	_Z14orderscenariosi
	movq	%rbp, %rsi
	movq	%r13, %rdi
	call	_ZN7FastMapC1ERK7Circuit
	movq	8+scenarios(%rip), %rax
	movq	scenarios(%rip), %r14
	movq	%rax, 72(%rsp)
	cmpq	%r14, %rax
	je	.L1742
	movl	nq(%rip), %eax
	xorl	%r12d, %r12d
	leaq	160(%rsp), %r15
	leal	(%rax,%rax), %ebx
	movq	848(%rsp), %rax
	movslq	%ebx, %rbx
	salq	$3, %rbx
	movq	%rax, 8(%rsp)
	movq	872(%rsp), %rax
	movq	%rax, (%rsp)
	movq	800(%rsp), %rax
	movq	%rax, 16(%rsp)
	movq	824(%rsp), %rax
	movq	%rax, 24(%rsp)
	leaq	80(%rsp), %rax
	movq	%rax, 48(%rsp)
	leaq	96(%rsp), %rax
	movq	%rax, 56(%rsp)
	leaq	128(%rsp), %rax
	movq	%rax, 64(%rsp)
	.p2align 4
	.p2align 3
.L1770:
	movl	8(%r14), %eax
	movq	(%r14), %rdx
	movl	%eax, 88(%rsp)
	movq	%rdx, 80(%rsp)
	testq	%rbx, %rbx
	je	.L1743
	movq	%rbx, %rdx
	movq	%r13, %rsi
	movq	%r15, %rdi
	call	memcpy@PLT
.L1743:
	movq	48(%rsp), %r10
	movq	56(%rsp), %r8
	vpxor	%xmm0, %xmm0, %xmm0
	movq	$0, 112(%rsp)
	movq	64(%rsp), %rcx
	vmovdqa	%xmm0, 96(%rsp)
	vmovdqa	%xmm0, 128(%rsp)
	movq	$0, 144(%rsp)
	movl	$3, %r9d
.L1745:
	movslq	8(%r10), %rsi
	testl	%esi, %esi
	js	.L1763
	movq	8(%rsp), %rax
	leaq	0(,%rsi,8), %r11
	movq	(%rax,%r11), %rdx
	movq	(%rsp), %rax
	movq	(%rax,%r11), %rax
	cmpl	$3, %r9d
	je	.L1747
	imulq	$480, %rsi, %rsi
	leaq	416(%r13,%rsi), %rdi
	movslq	12(%r10), %rsi
	testl	%esi, %esi
	js	.L1748
	leaq	(%rdi,%rsi,4), %rsi
	movzbl	1(%rsi), %ebp
	cmpb	$0, (%rsi)
	movb	%bpl, 39(%rsp)
	movzbl	2(%rsi), %ebp
	movb	%bpl, 38(%rsp)
	movzbl	3(%rsi), %ebp
	je	.L1754
	xorq	24(%r8), %rdx
.L1754:
	cmpb	$0, 39(%rsp)
	je	.L1753
	xorq	24(%rcx), %rdx
.L1753:
	cmpb	$0, 38(%rsp)
	je	.L1752
	xorq	24(%r8), %rax
.L1752:
	testb	%bpl, %bpl
	je	.L1748
	xorq	24(%rcx), %rax
.L1748:
	cmpl	$2, %r9d
	je	.L1747
	movslq	16(%r10), %rsi
	testl	%esi, %esi
	js	.L1747
	leaq	(%rdi,%rsi,4), %rsi
	cmpb	$0, (%rsi)
	movzbl	1(%rsi), %edi
	movzbl	2(%rsi), %ebp
	movb	%dil, 38(%rsp)
	movzbl	3(%rsi), %edi
	je	.L1757
	xorq	32(%r8), %rdx
.L1757:
	cmpb	$0, 38(%rsp)
	je	.L1758
	xorq	32(%rcx), %rdx
.L1758:
	testb	%bpl, %bpl
	je	.L1759
	xorq	32(%r8), %rax
.L1759:
	testb	%dil, %dil
	je	.L1747
	xorq	32(%rcx), %rax
	.p2align 4
	.p2align 3
.L1747:
	movq	%rdx, 16(%r8)
	movq	%rax, 16(%rcx)
	testq	%rdx, %rdx
	je	.L1765
	movq	16(%rsp), %rdi
	movq	(%rdi,%r11), %rdi
	.p2align 4
	.p2align 3
.L1764:
	tzcntq	%rdx, %rsi
	xorq	%rdi, (%r15,%rsi,8)
	blsr	%rdx, %rdx
	jne	.L1764
.L1765:
	testq	%rax, %rax
	je	.L1763
	movq	24(%rsp), %rdi
	movq	(%rdi,%r11), %rsi
	.p2align 4
	.p2align 3
.L1766:
	tzcntq	%rax, %rdx
	xorq	%rsi, (%r15,%rdx,8)
	blsr	%rax, %rax
	jne	.L1766
.L1763:
	subq	$4, %r10
	subq	$8, %r8
	subq	$8, %rcx
	decl	%r9d
	jne	.L1745
	movq	%r15, %rdi
	call	_Z14singlecriticalPKm
	vxorpd	%xmm1, %xmm1, %xmm1
	cltq
	addq	%rax, %r12
	vcvtsi2sdq	%r12, %xmm1, %xmm0
	vcomisd	40(%rsp), %xmm0
	ja	.L1769
	addq	$12, %r14
	cmpq	%r14, 72(%rsp)
	jne	.L1770
.L1769:
	movq	(%rsp), %rax
	testq	%rax, %rax
	je	.L1772
	movq	888(%rsp), %rsi
	movq	%rax, %rdi
	subq	%rax, %rsi
	call	_ZdlPvm@PLT
.L1772:
	movq	848(%rsp), %rdi
	testq	%rdi, %rdi
	je	.L1773
	movq	864(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L1773:
	movq	824(%rsp), %rdi
	testq	%rdi, %rdi
	je	.L1774
	movq	840(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L1774:
	movq	800(%rsp), %rdi
	testq	%rdi, %rdi
	je	.L1739
	movq	816(%rsp), %rsi
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
.L1739:
	movq	58504(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L1816
	addq	$58520, %rsp
	.cfi_remember_state
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
.L1742:
	.cfi_restore_state
	movq	872(%rsp), %rax
	xorl	%r12d, %r12d
	movq	%rax, (%rsp)
	jmp	.L1769
.L1816:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE5793:
	.size	_Z13criticalscoreRK7Circuitd, .-_Z13criticalscoreRK7Circuitd
	.section	.text._ZNSt12_Destroy_auxILb0EE9__destroyIP5LayerEEvT_S4_,"axG",@progbits,_ZNSt12_Destroy_auxILb0EE9__destroyIP5LayerEEvT_S4_,comdat
	.p2align 4
	.weak	_ZNSt12_Destroy_auxILb0EE9__destroyIP5LayerEEvT_S4_
	.type	_ZNSt12_Destroy_auxILb0EE9__destroyIP5LayerEEvT_S4_, @function
_ZNSt12_Destroy_auxILb0EE9__destroyIP5LayerEEvT_S4_:
.LFB7231:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	movq	%rsi, %rbp
	movq	%rdi, %rbx
	subq	$8, %rsp
	.cfi_def_cfa_offset 32
	cmpq	%rsi, %rdi
	je	.L1822
	.p2align 4
	.p2align 3
.L1821:
	movq	80(%rbx), %rdi
	testq	%rdi, %rdi
	je	.L1819
	movq	96(%rbx), %rsi
	addq	$104, %rbx
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	cmpq	%rbx, %rbp
	jne	.L1821
.L1822:
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L1819:
	.cfi_restore_state
	addq	$104, %rbx
	cmpq	%rbx, %rbp
	jne	.L1821
	addq	$8, %rsp
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE7231:
	.size	_ZNSt12_Destroy_auxILb0EE9__destroyIP5LayerEEvT_S4_, .-_ZNSt12_Destroy_auxILb0EE9__destroyIP5LayerEEvT_S4_
	.section	.text.unlikely
	.align 2
.LCOLDB77:
	.text
.LHOTB77:
	.align 2
	.p2align 4
	.type	_ZNSt6vectorI5LayerSaIS0_EEaSERKS2_.isra.0, @function
_ZNSt6vectorI5LayerSaIS0_EEaSERKS2_.isra.0:
.LFB7579:
	.cfi_startproc
	.cfi_personality 0x9b,DW.ref.__gxx_personality_v0
	.cfi_lsda 0x1b,.LLSDA7579
	cmpq	%rdi, %rsi
	je	.L1893
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
	movq	%rdi, %r12
	subq	$24, %rsp
	.cfi_def_cfa_offset 80
	movq	8(%rsi), %r14
	movq	(%rsi), %rdx
	movq	%rsi, %rbx
	movq	(%rdi), %rbp
	movq	16(%rdi), %rax
	movq	%r14, %r13
	subq	%rdx, %r13
	subq	%rbp, %rax
	cmpq	%r13, %rax
	jb	.L1898
	movq	8(%rdi), %rax
	movq	%rax, (%rsp)
	subq	%rbp, %rax
	movq	%rax, %rcx
	cmpq	%rax, %r13
	ja	.L1849
	testq	%r13, %r13
	jle	.L1896
	movq	%r13, %r15
	movabsq	$5675921253449092805, %rax
	leaq	80(%rbp), %r14
	leaq	80(%rdx), %rbx
	sarq	$3, %r15
	imulq	%rax, %r15
	.p2align 4
	.p2align 3
.L1851:
	vmovdqu	-80(%rbx), %xmm1
	movq	%rbx, %rsi
	movq	%r14, %rdi
	addq	$104, %rbx
	addq	$104, %r14
	vmovdqu	%xmm1, -184(%r14)
	vmovdqu	-168(%rbx), %xmm2
	vmovdqu	%xmm2, -168(%r14)
	vmovdqu	-152(%rbx), %xmm3
	vmovdqu	%xmm3, -152(%r14)
	vmovdqu	-136(%rbx), %xmm4
	vmovdqu	%xmm4, -136(%r14)
	vmovdqu	-120(%rbx), %xmm5
	vmovdqu	%xmm5, -120(%r14)
.LEHB73:
	call	_ZNSt6vectorISt4pairIiiESaIS1_EEaSERKS3_.isra.0
	decq	%r15
	jne	.L1851
	testq	%r13, %r13
	movl	$104, %eax
	cmovg	%r13, %rax
	addq	%rax, %rbp
	.p2align 4
	.p2align 3
.L1896:
	cmpq	%rbp, (%rsp)
	je	.L1897
.L1856:
	movq	80(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L1853
	movq	96(%rbp), %rsi
	addq	$104, %rbp
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	cmpq	%rbp, (%rsp)
	jne	.L1856
.L1897:
	addq	(%r12), %r13
.L1848:
	movq	%r13, 8(%r12)
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
.L1898:
	.cfi_restore_state
	testq	%r13, %r13
	je	.L1868
	movabsq	$9223372036854775800, %rax
	cmpq	%rax, %r13
	ja	.L1899
	movq	%r13, %rdi
	movq	%rdx, 8(%rsp)
	call	_Znwm@PLT
.LEHE73:
	movq	8(%rsp), %rdx
	movq	%rax, (%rsp)
.L1827:
	movq	(%rsp), %rbp
	movq	%rdx, %rbx
	cmpq	%rdx, %r14
	je	.L1839
	.p2align 4
	.p2align 3
.L1838:
	vmovdqu	(%rbx), %xmm5
	vmovdqu	16(%rbx), %xmm6
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqu	32(%rbx), %xmm7
	vmovdqu	48(%rbx), %xmm1
	vmovdqu	64(%rbx), %xmm2
	movq	88(%rbx), %rax
	subq	80(%rbx), %rax
	vmovdqu	%xmm0, 80(%rbp)
	movq	$0, 96(%rbp)
	vmovdqu	%xmm5, 0(%rbp)
	vmovdqu	%xmm6, 16(%rbp)
	vmovdqu	%xmm7, 32(%rbp)
	vmovdqu	%xmm1, 48(%rbp)
	vmovdqu	%xmm2, 64(%rbp)
	je	.L1869
	movabsq	$9223372036854775800, %rcx
	movq	%rax, %r15
	cmpq	%rcx, %rax
	ja	.L1900
	movq	%rax, %rdi
.LEHB74:
	call	_Znwm@PLT
.LEHE74:
.L1833:
	vpbroadcastq	%rax, %xmm0
	addq	%rax, %r15
	vmovdqu	%xmm0, 80(%rbp)
	movq	%r15, 96(%rbp)
	movq	88(%rbx), %rsi
	movq	80(%rbx), %rdi
	cmpq	%rdi, %rsi
	je	.L1836
	subq	%rdi, %rsi
	xorl	%edx, %edx
	.p2align 4
	.p2align 3
.L1837:
	movq	(%rdi,%rdx), %rcx
	movq	%rcx, (%rax,%rdx)
	addq	$8, %rdx
	cmpq	%rdx, %rsi
	jne	.L1837
	addq	%rsi, %rax
.L1836:
	addq	$104, %rbx
	movq	%rax, 88(%rbp)
	addq	$104, %rbp
	cmpq	%rbx, %r14
	jne	.L1838
.L1839:
	movq	8(%r12), %rbx
	movq	(%r12), %rbp
	cmpq	%rbp, %rbx
	je	.L1832
	.p2align 4
	.p2align 3
.L1831:
	movq	80(%rbp), %rdi
	testq	%rdi, %rdi
	je	.L1844
	movq	96(%rbp), %rsi
	addq	$104, %rbp
	subq	%rdi, %rsi
	call	_ZdlPvm@PLT
	cmpq	%rbp, %rbx
	jne	.L1831
.L1846:
	movq	(%r12), %rbp
.L1832:
	testq	%rbp, %rbp
	je	.L1847
	movq	16(%r12), %rsi
	movq	%rbp, %rdi
	subq	%rbp, %rsi
	call	_ZdlPvm@PLT
.L1847:
	movq	(%rsp), %rax
	addq	%rax, %r13
	movq	%rax, (%r12)
	movq	%r13, 16(%r12)
	jmp	.L1848
	.p2align 4
	.p2align 3
.L1853:
	addq	$104, %rbp
	jmp	.L1896
	.p2align 4
	.p2align 3
.L1893:
	.cfi_def_cfa_offset 8
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.p2align 4
	.p2align 3
.L1849:
	.cfi_def_cfa_offset 80
	.cfi_offset 3, -56
	.cfi_offset 6, -48
	.cfi_offset 12, -40
	.cfi_offset 13, -32
	.cfi_offset 14, -24
	.cfi_offset 15, -16
	movq	%rax, %r15
	movabsq	$5675921253449092805, %rsi
	sarq	$3, %r15
	imulq	%rsi, %r15
	testq	%rax, %rax
	jle	.L1857
	addq	$80, %rbp
	leaq	80(%rdx), %r14
	.p2align 4
	.p2align 3
.L1858:
	vmovdqu	-80(%r14), %xmm6
	movq	%r14, %rsi
	movq	%rbp, %rdi
	addq	$104, %r14
	addq	$104, %rbp
	vmovdqu	%xmm6, -184(%rbp)
	vmovdqu	-168(%r14), %xmm7
	vmovdqu	%xmm7, -168(%rbp)
	vmovdqu	-152(%r14), %xmm1
	vmovdqu	%xmm1, -152(%rbp)
	vmovdqu	-136(%r14), %xmm2
	vmovdqu	%xmm2, -136(%rbp)
	vmovdqu	-120(%r14), %xmm3
	vmovdqu	%xmm3, -120(%rbp)
.LEHB75:
	call	_ZNSt6vectorISt4pairIiiESaIS1_EEaSERKS3_.isra.0
.LEHE75:
	decq	%r15
	jne	.L1858
	movq	8(%r12), %rax
	movq	(%r12), %rbp
	movq	8(%rbx), %r14
	movq	(%rbx), %rdx
	movq	%rax, (%rsp)
	subq	%rbp, %rax
	movq	%rax, %rcx
.L1857:
	leaq	(%rdx,%rcx), %rbx
	cmpq	%r14, %rbx
	je	.L1859
	movq	(%rsp), %rbp
	.p2align 4
	.p2align 3
.L1865:
	vmovdqu	(%rbx), %xmm4
	vmovdqu	16(%rbx), %xmm5
	vpxor	%xmm0, %xmm0, %xmm0
	vmovdqu	32(%rbx), %xmm6
	vmovdqu	48(%rbx), %xmm7
	movq	88(%rbx), %rax
	subq	80(%rbx), %rax
	vmovdqu	%xmm4, 0(%rbp)
	vmovdqu	64(%rbx), %xmm4
	vmovdqu	%xmm5, 16(%rbp)
	vmovdqu	%xmm0, 80(%rbp)
	vmovdqu	%xmm6, 32(%rbp)
	vmovdqu	%xmm7, 48(%rbp)
	movq	$0, 96(%rbp)
	vmovdqu	%xmm4, 64(%rbp)
	je	.L1870
	movabsq	$9223372036854775800, %rcx
	movq	%rax, %r15
	cmpq	%rcx, %rax
	ja	.L1901
	movq	%rax, %rdi
.LEHB76:
	call	_Znwm@PLT
.L1860:
	vpbroadcastq	%rax, %xmm0
	addq	%rax, %r15
	vmovdqu	%xmm0, 80(%rbp)
	movq	%r15, 96(%rbp)
	movq	88(%rbx), %rsi
	movq	80(%rbx), %rdi
	cmpq	%rdi, %rsi
	je	.L1863
	subq	%rdi, %rsi
	xorl	%edx, %edx
	.p2align 4
	.p2align 3
.L1864:
	movq	(%rdi,%rdx), %rcx
	movq	%rcx, (%rax,%rdx)
	addq	$8, %rdx
	cmpq	%rdx, %rsi
	jne	.L1864
	addq	%rsi, %rax
.L1863:
	addq	$104, %rbx
	movq	%rax, 88(%rbp)
	addq	$104, %rbp
	cmpq	%rbx, %r14
	jne	.L1865
	jmp	.L1897
	.p2align 4
	.p2align 3
.L1870:
	xorl	%r15d, %r15d
	xorl	%eax, %eax
	jmp	.L1860
.L1868:
	movq	$0, (%rsp)
	jmp	.L1827
	.p2align 4
	.p2align 3
.L1844:
	
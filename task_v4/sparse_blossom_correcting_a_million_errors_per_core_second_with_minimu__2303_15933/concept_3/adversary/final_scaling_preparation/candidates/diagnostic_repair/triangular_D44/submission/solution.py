import os

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

import ctypes
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from scipy.special import ndtr


import base64
import zlib

NATIVE_IMAGE = (
    'c-rke3v?6Ll{5O-'
    '0*psaOzHp$PS3P84d_@v0tyf$TY_;aCvGssP6@)uGG^;v?QvpKmO7Qy%|sE9J;^TFkd*$m?Ae@#=Fl#?OIjJnHc1mcrXeikV@OLR9EdRqm=LVJ'
    '_q{jrXkw8x?b+S4$InN8@80|FeZTwey>Fy9-}iWz8hD;llaafV8-+N|$?~#gTHFF|68xXR-AwA5xb!KSnVNG}njxQA1MBnFn^SWwA8D_U;dS}P'
    'd}^-'
    'c%YaY+VhZ<{rsnMinm=Ml<ufq8LB=;&s>}J*+``yR?6Z@})93kIYOd$o&+6%OkxR|hxnKS#x%!K=SH}37*!=19d0c9)w)aio%iunLQkVB$)?T`'
    'G$Ty_syrx|%)0t&=ufTPQnuxxR(sLP%^f^a*W3^NLufMQqxO2tfzgd+1n^!+n*K@K)AGmggWcYY6(RZzJEQQaP$H4zBe6AY<Uy}yEAq{>_8vJ+'
    'D;Ga%|w`$f}n|7tCU!Mlgr;#%&4SofYlg({q!d{=o2tMDs`o;!di(J(#`+S_Qq`cHu9cT`$Ti+rFn#)Uz>lzyZ<yC9z0+cp3#piFU^3|+wsH$8'
    '4P=Kpj|D8bH`r5|EYR-3G!-Mr)eW1Q2AajAXCO}lzl|4|;)ithz@^X1jq0cARHa9-'
    '#s|z%&lWTo}=H|xcvTyjYXKii1ra*H`Bg&OG_#P<ad@C9rT;EXbyEo9%T8}NQZIP?}x87=NX|&yrV12T*&hPiNAY@0#Pw~r&i+yu#h1@c4Nl~$'
    'Hj%|*EE3T+;6_xnxwz-<3%|WYFR6zB4qt$J<QEfHC#{~b)pshTY31vR{cTBU+WnbMei39pza@~0DfQGI-{tp?rONNtlBlkN-'
    'M;m|S`R|x<M;LjE+i>{#Nx0jx87$BIdkgNaY5b`C)0%zVI(7X7?C;n3)cvg5nRccRF&*B?@MUE>yTsuBduX1au?0kq25-'
    '^e2Q~Of8vL*ZpQXW9l#S|nrUswK@R_6Lf!ZYv-l)MBXz*HpSg669HTVS@yw;97HTVe{yrjWT<i^u@8c*YCJdLOEG@ibAx***Au@rpYB8AN-mq3'
    '^iipqw>Au0HhrHjxLx19p?P~t1^LMF^0^=pwZ6hE0rB(@TmC-C7UY#?xF5;hX}S4r4J;2$SpGl3sZ!Wjg9ScReW+eqtf+FyY0*TE}vaH$UV=-'
    '|aVSTBFJ3QJ*GtdPPRMJa~kNrHv37YMjp#E4r8yTyEIW)DuEMN)cWPcq_8My%Bm+ZeH*5!)DXA_{JcRWkB6MqZ;OuZi7(WaWcc5#(Ow^gvuv-'
    'X7={W^~XvF|t^>6EpJ<FmnvcQ($RF7SpAjkmwg?;E9*(VmZ{WB=v8*7qgiok}@cDo?9Yy4jU!DM>;$r=YoLOm;g(nzlO|<%8&EazIe)=cm%k0g'
    '%n);C?4!3<xg^!6kdD|fS6+>k%(18Z+pyV0p{-q-'
    'W2}$gFw{4u9dEDxmLK!S4jRd%OxcyJ^cQDP%)`9wn*76=0nj7(_;lKQ_96A#Vg8Qr9<2U++O7|aVOA)(3z<m=TfeEBjQ;y%+Oh(W49S=ycdgIO'
    '(gD$OwX4ToLpr)o#|dWf5EG~e6tj3vq+9Ba#l&CTpYGvj6De~rJ+9x9U(K0Zb0gMH$zh1i9G{&DKak)MYTx^T~ku=dsA^%K@5}Y7?CGQk>w~%L'
    'MC8dqcUSP1(if$8uMwMT&N4WAoEdao1}C}odb)6ke#$Ky_=3ODs)UCy?ZB?p_81Ck_X3@{2!k{T|bD%ie)&-Lg<e-Qq?O1Aym2odS9YkBCQ-Jh'
    ')b~@$O(M`zCtfQECn};WxNDSQHZP6OO8jNJ(2HOP!A`SL{?&ZcLA3dG`Yg7Bx3iEijchg6()jp5>_ULBG_{5rH~anR$;#=MaqU_SFdP<Sx1Fg#'
    'uA2SU)iS$BhWXs!ghhMfhAIJhp3*CrCtz43mv3&6)CC6LVgrU9+|=7%hyTay&^ur@+zlb#1$ad9rlV%_7k4a%bRW<atT(`+p)*5;64Wx91?O&$'
    'E08vFF6KUPkBI9H{Y0ts<>CoLsJSirwQA#vbKaL_aUvoKnw&75{YHWj&z8UTJeb}K<c^qmVJ`HgKVEio)B9g1Dadq5}xlx&UST-'
    'u!`+G!FR*w1BAB$TpV%F=AisDD2Iv8JSVn6S?LPCI|5T|f^uYa0%zO86Xkr%!e)Of!r@h*i^f%8LzPuxfzow27L4&yFv?4v{ie_fYzCiDMNGfO'
    'UI63-u07aE;hrv~3lK5@gbNx(Mv%ON7>9lnaz6s)_Pu0yoY3)Am?Ag!(*t_Dx&8)@1D%k0p=0F@*qQBQN~LfIndchegQygNl>q!MVj6ReLxR-'
    ';tyqVIicTm?!&s0UhgwhLT;gb9M6%-;TG{PHie#h<1r<$QAo603VCxYc-Hui1T11=%>?n3H6rvKE!W6-'
    '8Co2M?envXBmrS}s`6PZXSy@E4Gq{Z9*rMZ@5aNmN*eF`0Py%<#ZlcOy)?>!Ylp-Z5F-'
    'D0GQ%YfyLiR6E4l+u9k}}A6e$6PgNy<(}d74q$l9YZ%d6-ewBq`e%WgSppcB%SF55I)g{@eGvR=MtXt#<jkP%*b@Hs2bx&_-'
    '1?28*A8i{H;QcPFEhKqcP&F|-RJ1~nqcqszGYO49G(a=Lk{6c$)UkNuAqgiT+W{UxFYUGB&%ZV&Fa66Gjv$IwM#^8o{`jt-'
    '~9|5}OveYYZtQs<w{ZlzANx|D7ylJ$F3`L+_}Rc~a`t&*`$thJwrUq|$#@@kDxaJWWT`3J~*!6;OA!N1kf8n;k@|5m;P|7??g0;>8@22{B!-'
    '#FwJDqpLSgob#HODMREJXetCW8`@m|GhpWta=@)RlElORviY26nbksLhdUy_yI=34K1%aS0hv$g_(c7MyNdE5^{2X1nnFJBoYq*0ayy&0OIdK&'
    '>^Vc{gD+g`vK|&1wROKa-'
    '&2lkymj5*p5=R%HKonXJAtm0J35~5PE>n34|^o$Nh{I?43ngNX>%K@c_?a9kh+P(}z5QHS1<*p%11hHxEXT;}!Ej)*1K=fxUb}+>Z~}g_Z9^>#'
    ')TNx`mm$#X}f33OUb-QG7yZzX)387OcPtEib-r3L$ogTd|f)SaliZq~I{heoWkfIGEf+P-'
    '8FIia43Qh>GHDzJU@fD8Yl40C>tls!Q+<leH6aHj2(z`$x3Fa?;@J|H>r|y2S-'
    'p5qsVZV4av3TL~4xG?2>4wi%ljssrE_ov_ZEI#C4<q9*>7NVC$;VU6u%ARzUoZIncZ4G20B!lO@JCEJS5l@NLqKpfRR><N5ci*E;vTZy^DqUa8'
    'T%AzH5@o&2Lw}QjG5Gu$4Q?!?Oj8H<@Y|Ejx5^atfHh~O#Y60^fP+Y{1x{e(jttwG3b4cS=3Yf*+LxQcSg_!(N;~0#p#u0Yb0;UxOAVXBeLyt('
    'P2OZAGZJnoScR%qR)1+-'
    '~h<9){N|ke9(*F)=cuJA{UBtTcwE7yJ+H2~nOkIep810Kfb;Y}IHxZ0Bp3bHHqF1@(ojDZSbOE9=aO|O%h0Pd$hiN~_o|nRpkv6?yDzvlT0HGV'
    '$5>)XF$?uSYo#0#c<%60R^@qRviKGmdL>7(M2cbev1}t1AQex7!l86cRPEMxeAHfPLWe{-ypsOhY$CSgBIQF;x7$O54IWKIk6qs{MdS0-'
    '6WV&20@+4Z`E$$(UNhb@;D8&3Eep-'
    'P3+38URJp5Ta^W;e|OlOI|`|il1w>ZLk!ej5lst{z(A~B*{IVN?UHXe?7m5riRQeN>!YOIkq(6D2{e(=@3yi18HCJ|S3fz<h)sRY`)JCc<l%y4'
    'q0kwqqNWO`wVqt_)o+lxNe3l8nssM|6ubo4+h8N331`$Z^#C7olBGP?~H$eNW|0|AwR*`PyUYC6G`8DJJonJ7qd^tQg?m@dj+y(?mx03+bht>Z'
    'FeA`eU-Z2MK6IPG7;Y4q@CV9Mu8d|cwscpOKCEvvz;dK~A3EoVkB-lWrpnuOmCpzA<A3DXS-vS)SKPk^9VB8&8XaUM5fr3v92)7u#8Io|sIDO?'
    'kBm@ErY34EC5=+SYVO8B>d+9W|(fNBR=)UJhU@ZiVo%ht|=9_bdC9anG!=BaNo_OBe49M-'
    'MS9>p~*z*z!EVqFANRnZGQ;pyzqn5(rvOd}e%V^F?T@*g59<K_pYZ7?KL7X~y(aP0~)UOhzHnZi?lO10{DJW+!yUf?Xmmh(J(LOJe^EKex!l=y'
    'oOpSdSee#8=dZ$#=mX^b?(`L$fM+WS2Amz71L6zqX8@I9lK=@V71&eJBZa?BesIlPf7>(<i9^jvQwH>bpL#2dNK>J*;sE_HzGdbZ1D84x;7@Jv'
    'zqaOXv)^Y%V^UL|^RJ<fntrzciilj~t4!b}`Z>PaqgFMxqh#5FYP_2hb(1A~XZ3>9;{e9YrGAZ)23N-`pB`52TW8N7p??*opn9~C-'
    '^Ceomu1n$t+iFAAJAlB?>1Z_VHP2Tj2Y--;MaYvT$FQJVh5o(FB=^Z%X415hd-{i-'
    '$QQ1}>z%`Me@Cx)PD<%cIc^9ba=0BK;o3mD*MZShh#Ni05PYnsa4{-?d-'
    'iM~L24G~T5tN}CxSEFy@=pQv(h&7<=yxIb%@M`ePtFl<LSU;X5?|C#^_|qL?8HueGMRMhRhXz@;!Ckg93N@au;(dm(F!{l?EZe-_t=L*G-'
    'BurQf67mDMJbF!r>C!zwsJ8-'
    '5Eh&N|de|oBF&1N0>E<tWgO>6#8{qK8*j}lZL&H<E=;HcWGBf2pu%j1t~<ZwG3Sg9%h2nWAV5R3#dCl7`Gx|(9c0eeG?wO0Kg@5(6f~gDuzfq{'
    '<ROudA%tV-Lx}Ioudbi&tNk4P<OdieE{bcHcjry0-1QSkGO*-)scni=?9=FbEm|2!me<-'
    'B1>T$Q3EyAVOGEG6L%O40l4b>jMU=Ss<uf|F#4L;6>;*gogsP<yCO>sw3rJ;BSwTTN!uV>iQx^HFjTfKL?1^X(WH=BC<H^NtE76tYfxT!8F{8N'
    'nP6cEBasUgFKFbNh}=#jLmaZw{OTkUvb;ymcu3lZq(h`TR6i<uh#^w;K@ksBC+JzM(%m(TwGJS)U<d<Vq2g7n10UE5mENvlBw1+n9H>stnGTpS'
    'q2mcWU5?yxR5{-nx7yF!FBZm?!%pGp9``Ms$}62`toBzxE1%vc{H8B-'
    'Q7%sQ=^$>Uu9{Mz;XDrMaHvnd6T6S9&y%67{L1BtB%gAAA{kM`@%VgHe<A{BgN%*LT&S;gAK}JXj^{uvS1<v_>$?`MRsAhF%QAg;D;LnZT9|dc'
    'IBH#c{&MRo%;1=Poe2Ad+Sg~mz8-f8&rtj7QSIv@YF{mXo_!tqGwtj7q<uZ8+Sg0Mmf;Z+KEI61>qPCx{fjpCAkK;fPnM66h%Wb-JxY6%+lO7_'
    'YlPMNpf?8U_j+2-'
    'plaje0|$MuAd6IHBsY)g4k&E01z~k3aed5No3IMHZrmHDr0YihAl;Fcg>(xGp$afw9%Ur{6ghFC9b}g5^V%=)cVNFT{6NL9j=Edohc}z~q~n!v'
    '60D!Y@#bAiHLN<-'
    'Q2lNiy*Q`_Xg$U+;&+GsDt`A0&JH_TFk_1mKFrqwF4gGbV;(>|4eZ=NBPcMOPx3gUxCg&w!pM%8*Htu(k}!Bjg(9)0brw%l1P-'
    '*_Fc2eAsf8?*I*|;ehGn}NN*PhuHl|X<WmlRGVadV*Drk0dE(@rvqg!9Q<*lD%%l|dkwN%~j?*EZ^YV7@v>k6@KQ>aha{1kPJWUE0;Yaw0^k65'
    '^baKwTZZt%j%3!lECKh1&_EA{6_0Y3o_T=}l>#;6Hq{*|F3==)Kxf=?J+F|Yp(`^S>Mk2njUWE}-'
    '`$sl{|N1<Vf_#o_Wg^Bdq)Ja^*!Y9ZHvh^R`{6=vB9-?`AI1g@w?JtCWPV{jk{`e&t!Q{cd|6=jWaTdR@2=d?AS-OBdiP}NKv76SR?qc9iO(3c'
    'q1ZM>oz=FXDe0Xr2ho)@aKJ35C(ewQ`;~!p3BydZh#>EFe8SN=u??2B@-'
    'G}_FL+ayI?AQS#e#5hA_EC&aBD0Qp!_{ITKEIdjC(!x7H82A_CwTJJ2T4E+GPB;n<C4qqwy@a%#uIxWzKL<@Tg16u#Ye0d)<W=l0LJzS`cvdv^'
    'd^L|FR)OSJOYA%mW8r!yvst_JT;VkZZwp&VkisaijgNt?Hui~Xe3S@yY^~)4Sru0T08`C-lg+s(4F)db^PQ&B7qj-gJ}HyI4G_DnMT}t1}ntlS'
    '4anL`mKQ;(+cS#VK6Yj773f5m0X{b@$!!dXY~;AeP@%Mi%&j--}Nk>3!-'
    '9gpVG$J<h!k%%*5dX)cAX}ZYI`!;S?!ffeyz08Ovewd^}@FLc@M&=)!O!LB1STy5m#c9W8%+YP396gFm9d2Q>KAP}Y9Wocv~aJpErt{;GzCMmg'
    'W#9H^25`7Ltw9d|qs@XL+O`E^yz>jKUBa&1*ZetlJ&uVwv1fr6PTU*(12eKQ(<&OcY&cliG1Ig8k@FPEr4_e^c&&=NK0rx_Q{W50#m^-'
    'dyzKWi-PPbBbBz7ujZo4X*N4r-YXDz%?U$W?#0`p~@`-'
    ')7~fWo26M(J}rGemee+6J(J_v#m?B^X?KRJ!om?mQ20l>vP2~tNd=(rd883#IM5N$pgMggP)#kugptY%zS$G433+owp+%2gI{(sk-'
    '*<Lo4$iT4$ro3F%)IzZ8jEV=SNIM*#(c8UD<^{%y4Hf2xi`u-EK0TGf&K3061560n~xIMcLM(Y>R6W`<*V%!(-'
    '4F+_t8298bF`nEAtu$IKDaX5$v}Q`AI)clcoff61F)oX-vL=9lMl-3If|=X3vRG)Lxh=Zxm3=5zmPGXH8m_u}nPF@8G|Ke`=>z-)esH;-'
    '%ncp6XRX*`Xm@id;s(|8(B|NoMD?@qmEr{1Ca9hV9p(80%a@M)GO@6NG9)MN(M+Gu_wgVp<g>h(|cj^0$3tM>q>>*ybiBpS&{l3lt}4=T0nQk{'
    'BNE{|QlQ}4pfWgS)T{N=Gcc}I`kpHuJh?bMws)w_RRQu#Ae@f8`V{fx4Fg08)h1nvJG*6{>`)jNTM4BpP@ml<sQU(yft9=kpjvh{Vcyo}{*Sl-'
    '0)c9w5d>y@R-Syo(pM}EPIwXF?uYrfrXn`bMWZEq!@ebbydw!(R~xicBzTK%N={?8}$cq>`cY%V`1bzSq*)W4P0Ka`V-'
    'pUv?4OVCb+ck1xpB7K_5ttm_0Cu>Q0N>aboq%b+{Iyq00`nk#d!hJ^nca!?pal7oFo};nq?<4<nlK1)5^g5Aq<EPf^6vJ2O?&FS-{tL-'
    '{o@|px{KV0Vz${I~Z^^kEKBZsR^HlyCUAr>~J}<dX)pQ#__I-'
    'Q&5!zVy)gMZOkEFqGPlNwu8hjT&_Wkw)Y3iTj$G#^&(J*%XThie13&^qLEJ=gc+>N*So0?L<#=2_G-z>Mttu-|^KR0>{-zV4m{CL~Gh4cBU8-'
    '45Q8rN3U`Ksl{<`!R7Ya8cptZ%9d$bo9utYg-'
    '|yZP&VRn5&+8+?HVxp@Ou(_B>_@Kv|g*KYt84djEGa!OU7Z|S|RQjgDbw;SIO;9GY03ZF+}NXdOKHrdkXtF3CNt_yJPmA2+Ujcx4P``8VRw7~h'
    '?m3O;JONxQJytG&qzRY`1k<075XX(=Ao^oHgtH|r|>0U43)LzEF<|_o8+AI9@9Rw-Nb&czsnim0(cNL`Yu$L7$Q{D@peY?RJgVa>M_S+Ov-'
    'ellZUrZ2aYf9<U7_Vm-Qygb&*-$T6t%Y1}rg^PeYG{-'
    'Lwsj4ywx;Gr=&Za!gIe3VzOH)q`f83qwN)*(oUM980|=wJ+)ODCz#!K*HlzSPpfv~Ts<0v}HPy+SjjS&gZR;9Yp(WtwY;vFtK%xV-'
    '=EmwOxr(y|YMJuYRyU7A(2U>j3$*zIO|nlW1GJ6mC6%F;q4BEv^&lP^qwQ14Yg<}4*i`lPpv8Z&Kc2>=zH=bmdt5kO+@vO(jz8V|V@7>OYI4En'
    'BE%#rzZ!=P>iA7*+W!WN!3?@MP0iJ7DrV+0ExPz=Ig5o1y0}lx=klM93$*FmEap=A)i_Jdr|bG}(B-u(hEriRj#Kj;+-'
    'UzzV~qbnhBxTqMm3M7nLl;>4>MYkE)G@mof`hUG5Eur=G``$I9<)Bea8C#P{*HdP0icKh`+S?<2wEw*3{hk8T|jG<KJaX&6_@h|EK!?=cMMIo5'
    'to>)4%BW)p$qECx6ELJ<s@)?+nqspDJDd)%0&V{&eqSO4ok3j(=xiYM#Yk+kPC>@$a^$=1aM2@4u7q$<~}_lJ9p~Ja&5)U5>Xk1r5I%N5?)V|7'
    'EszM&0=)`Tj0G^;~Jut;3USOv(PU_r~-'
    'uxwidPa|55spNwansbD((NjiQtJ}+~QtuOld$l)nY<yYhEHO{f?>(}oF*1rBQrt;5D!>`Q^WB9eLj9+3M!)<uO81`#InzQh+VwzVPuHFBfH2n6'
    'Zqvwok@&7lih!6G'
)
def load_native():
    image = zlib.decompress(base64.b85decode(NATIVE_IMAGE))
    try:
        descriptor = os.memfd_create('detector_calibration', os.MFD_CLOEXEC)
        try:
            with os.fdopen(os.dup(descriptor), 'wb') as native_file:
                native_file.write(image)
            return ctypes.CDLL('/proc/self/fd/' + str(descriptor))
        finally:
            os.close(descriptor)
    except (AttributeError, OSError):
        import tempfile
        with tempfile.NamedTemporaryFile(dir=Path(__file__).parent, suffix='.so') as native_file:
            native_file.write(image)
            native_file.flush()
            return ctypes.CDLL(native_file.name)


LIBRARY = load_native()
NATIVE = LIBRARY.likelihood
NATIVE.restype = ctypes.c_double
NATIVE.argtypes = [ctypes.c_int] * 4 + [ctypes.c_void_p] * 9


def pointer(array):
    return None if array is None else array.ctypes.data


def project(values, detectors):
    result = np.zeros_like(values, dtype=np.int32)
    for index, detector in enumerate(detectors):
        result |= ((values >> detector) & 1).astype(np.int32) << index
    return result


def neighborhoods(spec, size):
    dimension = spec['detector_count']
    if size >= dimension:
        return [list(range(dimension))]
    distance = np.full((dimension, dimension), dimension + 1, dtype=int)
    np.fill_diagonal(distance, 0)
    for first, second in spec['detector_edges']:
        distance[first, second] = distance[second, first] = 1
    for detector in range(dimension):
        distance = np.minimum(distance, distance[:, detector, None] + distance[None, detector, :])
    candidates = []
    for center in range(dimension):
        chosen = [center]
        while len(chosen) < size:
            remaining = [detector for detector in range(dimension) if detector not in chosen]
            selected = min(remaining, key=lambda detector: (distance[center, detector],
                           distance[detector, chosen].sum(), detector))
            chosen.append(selected)
        candidates.append(tuple(sorted(chosen)))
    return [list(block) for block in sorted(set(candidates))]


class Model:
    def __init__(self, spec, size=9):
        self.spec = spec
        self.bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
        self.exposures = np.ascontiguousarray([action['exposures'] for action in spec['actions']], dtype=float)
        self.weights = np.ascontiguousarray([action['mode_weights'] for action in spec['actions']], dtype=float)
        self.alternates = np.ascontiguousarray([action['alternate_probability'] for action in spec['actions']], dtype=float)
        self.original_masks = np.asarray([channel['masks'] for channel in spec['channels']], dtype=np.int64)
        self.blocks = neighborhoods(spec, size)
        self.masks = np.ascontiguousarray([project(self.original_masks, block) for block in self.blocks], dtype=np.int32)
        self.states = 1 << len(self.blocks[0])
        self.actions, unused, self.channels = self.exposures.shape
        self.counts = np.zeros((self.actions, len(self.blocks), self.states))
        self.spent = np.zeros(self.actions, dtype=int)
        self.groups = np.array([[channel['family'] == family for channel in spec['channels']]
                               for family in ('boundary', 'bulk', 'hook', 'rare')], dtype=float)
        self.groups /= self.groups.sum(axis=1, keepdims=True)

    def add(self, action, syndromes, counts):
        for block, detectors in enumerate(self.blocks):
            self.counts[action, block] += np.bincount(project(syndromes, detectors), weights=counts, minlength=self.states)
        self.spent[action] += int(np.sum(counts))

    def evaluate(self, point, counts=None):
        point = np.ascontiguousarray(point)
        gradient = np.zeros(self.channels)
        value = NATIVE(self.actions, len(self.blocks), self.channels, self.states,
                       *map(pointer, (self.masks, self.exposures, self.weights, self.alternates,
                                      point, self.counts if counts is None else counts, gradient, None, None)))
        return value, gradient

    def distribution(self, point, action):
        point = np.ascontiguousarray(point)
        probability = np.empty((len(self.blocks), self.states))
        derivative = np.empty((len(self.blocks), self.channels, self.states))
        gradient = np.zeros(self.channels)
        NATIVE(1, len(self.blocks), self.channels, self.states,
               *map(pointer, (self.masks, self.exposures[action], self.weights[action], self.alternates[action],
                              point, None, gradient, probability, derivative)))
        return probability, derivative

    def fit(self, initial=None, scale=None, maxiter=100, deadline=47):
        start = self.bounds.mean(axis=1) if initial is None else np.asarray(initial)
        scale = np.ones(self.channels) if scale is None else np.asarray(scale)
        scale = np.clip(scale, 0.025, 1.0)
        total = max(float(self.spent.sum()) * len(self.blocks), 1)
        best = [np.inf, start.copy(), np.zeros(self.channels)]
        duration = [0.0]

        def objective(standardized):
            if time.process_time() + 1.3 * duration[0] > deadline and np.isfinite(best[0]):
                raise TimeoutError()
            point = start + standardized * scale
            began = time.process_time()
            value, gradient = self.evaluate(point)
            duration[0] = time.process_time() - began
            if value < best[0]:
                best[:] = [value, point.copy(), gradient.copy()]
            return value / total, gradient * scale / total

        limits = (self.bounds - start[:, None]) / scale[:, None]
        try:
            result = minimize(objective, np.zeros(self.channels), method='L-BFGS-B', jac=True,
                              bounds=limits.tolist(), options={'maxiter': maxiter, 'ftol': 1e-12,
                              'gtol': 2e-8, 'maxls': 15, 'maxcor': 15})
            self.fitted_gradient = best[2]
            return best[1]
        except TimeoutError:
            self.fitted_gradient = best[2]
            return best[1]

    def sample(self, point, action, samples, rng, importance=False):
        modes = rng.choice(2, samples, p=self.weights[action])
        rates = np.exp(point)
        syndromes = np.zeros(samples, dtype=np.int64)
        log_weights = np.zeros(samples)
        for channel in range(self.channels):
            probability = -0.5 * np.expm1(-2 * self.exposures[action, modes, channel] * rates[channel])
            proposal = np.maximum(probability, 0.02) if importance else probability
            firing = rng.random(samples) < proposal
            if importance:
                log_weights += np.where(firing, np.log(np.maximum(probability, 1e-300) / proposal),
                                        np.log1p(-probability) - np.log1p(-proposal))
            alternate = rng.random(samples) < self.alternates[action, channel]
            syndromes ^= np.where(firing, self.original_masks[channel, alternate.astype(int)], 0)
        return (syndromes, np.exp(log_weights)) if importance else syndromes

    def fisher(self, point, samples=3000):
        information = np.zeros((self.actions, self.channels, self.channels))
        curvature = np.zeros_like(information)
        rng = np.random.default_rng(67492)
        identity = np.eye(self.channels)
        for action in range(self.actions):
            probability, derivative = self.distribution(point, action)
            normalized = derivative / np.sqrt(probability[:, None, :])
            hessian = np.sum(normalized @ normalized.transpose(0, 2, 1), axis=0)
            curvature[action] = hessian
            syndromes, sample_weights = self.sample(point, action, samples, rng, importance=True)
            scores = np.zeros((self.channels, samples))
            for block, detectors in enumerate(self.blocks):
                codes = project(syndromes, detectors)
                scores += derivative[block][:, codes] / probability[block, codes][None, :]
            covariance = (scores * sample_weights[None, :]) @ scores.T / samples
            ridge = 1e-7 * max(np.max(np.diag(covariance)), 1e-5)
            information[action] = hessian @ np.linalg.solve(covariance + ridge * identity, hessian)
            information[action] = (information[action] + information[action].T) * 0.5
            scaled = 2 * self.exposures[action] * np.exp(point)[None, :]
            ideal = np.sum(self.weights[action, :, None] * scaled ** 2 * np.exp(-2 * scaled)
                           / np.maximum(-np.expm1(-2 * scaled), 1e-300), axis=0)
            active = ideal > 1e-10
            roots = np.sqrt(np.maximum(ideal, 1e-10))
            normalized = information[action] / roots[:, None] / roots[None, :]
            normalized[~active, :] = 0
            normalized[:, ~active] = 0
            eigenvalues, eigenvectors = np.linalg.eigh(normalized)
            information[action] = ((eigenvectors * np.clip(eigenvalues, 0, 1)) @ eigenvectors.T) * roots[:, None] * roots[None, :]
        return information, curvature


def design(model, fitted, fisher, spent, total):
    channel_count = model.channels
    identity = np.eye(channel_count)
    base = np.einsum('a,akl->kl', spent, fisher) + 0.1 * identity
    remaining = total - spent.sum()
    prior = np.diag(12 / np.diff(model.bounds, axis=1).ravel() ** 2)
    base += prior

    def objective(allocation):
        information = base + np.einsum('a,akl->kl', remaining * allocation, fisher)
        inverse = cho_solve(cho_factor(information, lower=True, check_finite=False), identity, check_finite=False)
        variances = model.groups @ np.diag(inverse)
        value = np.sum(variances ** 0.8)
        channel_weights = (0.8 * variances ** -0.2) @ model.groups
        sensitivity = (inverse * channel_weights[None, :]) @ inverse
        gradient = -remaining * np.einsum('akl,kl->a', fisher, sensitivity)
        return value, gradient

    start = np.full(model.actions, 1 / model.actions)
    normalization = objective(start)[0]

    def normalized(allocation):
        value, gradient = objective(allocation)
        return value / normalization, gradient / normalization

    result = minimize(normalized, start, method='SLSQP', jac=True, bounds=[(0, 1)] * model.actions,
                      constraints=[{'type': 'eq', 'fun': lambda allocation: allocation.sum() - 1,
                                    'jac': lambda allocation: np.ones(model.actions)}],
                      options={'maxiter': 80, 'ftol': 1e-8})
    allocation = np.maximum(result.x, 0)
    if not np.isfinite(allocation).all() or allocation.sum() == 0:
        allocation = start
    return allocation / allocation.sum()


def posterior(center, covariance, bounds):
    mean = center.copy()
    variance = covariance.copy()
    precisions = np.zeros(len(center))
    locations = np.zeros(len(center))
    for iteration in range(8):
        for channel in range(len(center)):
            marginal_variance = max(variance[channel, channel], 1e-12)
            cavity_precision = max(1 / marginal_variance - precisions[channel], 1e-9)
            cavity_variance = 1 / cavity_precision
            cavity_mean = cavity_variance * (mean[channel] / marginal_variance - locations[channel])
            deviation = np.sqrt(cavity_variance)
            lower, upper = (bounds[channel] - cavity_mean) / deviation
            if lower < -9 and upper > 9:
                continue
            mass = ndtr(upper) - ndtr(lower)
            if mass < 1e-12:
                continue
            first = np.exp(-0.5 * lower * lower) / np.sqrt(2 * np.pi)
            second = np.exp(-0.5 * upper * upper) / np.sqrt(2 * np.pi)
            shift = (first - second) / mass
            truncated_mean = cavity_mean + deviation * shift
            truncated_variance = cavity_variance * max(0.005, 1 + (lower * first - upper * second) / mass - shift * shift)
            precision = max(0, 1 / truncated_variance - cavity_precision)
            location = truncated_mean / truncated_variance - cavity_mean * cavity_precision
            delta_precision = 0.7 * (precision - precisions[channel])
            delta_location = 0.7 * (location - locations[channel])
            column = variance[:, channel].copy()
            denominator = 1 + delta_precision * marginal_variance
            mean += column * (delta_location - delta_precision * mean[channel]) / denominator
            variance -= np.outer(column, column) * delta_precision / denominator
            precisions[channel] += delta_precision
            locations[channel] += delta_location
    return np.clip(mean, bounds[:, 0], bounds[:, 1]), variance


def integer_allocation(fractions, total):
    exact = fractions * total
    allocation = np.floor(exact).astype(int)
    remainder = total - allocation.sum()
    if remainder:
        allocation[np.argsort(exact - allocation)[-remainder:]] += 1
    return allocation


def calibrate(spec, query):
    model = Model(spec, size=9)
    budget = spec['shot_budget']
    maximum = spec['max_shots_per_query']
    queries = 0
    records = []

    def collect(allocation):
        nonlocal queries
        for action in np.flatnonzero(allocation):
            remaining = int(allocation[action])
            while remaining:
                shots = min(remaining, maximum)
                syndromes, counts = query(int(action), shots)
                model.add(action, syndromes, counts)
                records.append((action, syndromes, counts))
                remaining -= shots
                queries += 1

    exposure = model.exposures[:, 0]
    amplified = exposure >= 2
    rare = np.array([channel['family'] == 'rare' for channel in spec['channels']])
    general = (amplified[:, ~rare].any(axis=1) | (amplified.sum(axis=1) > 1)) & (exposure.min(axis=1) < 1)
    pilot = np.where(general, 160, 0)
    for channel in np.flatnonzero(rare):
        candidates = np.flatnonzero((amplified.sum(axis=1) == 1) & amplified[:, channel])
        for gain in (120, 720):
            selected = candidates[np.argmin(np.abs(np.log(exposure[candidates, channel] / gain)))]
            pilot[selected] = 140
    collect(pilot)
    fitted = model.fit()
    fisher = None
    for target in (10000, 24000, budget):
        fisher, curvature = model.fisher(fitted)
        fractions = design(model, fitted, fisher, model.spent, budget)
        total = target - int(model.spent.sum())
        fractions[fractions * total < 100] = 0
        fractions /= fractions.sum()
        allocation = integer_allocation(fractions, total)
        future_queries = int(np.ceil((budget - target) / maximum))
        available_queries = spec['max_queries'] - queries - future_queries
        while np.sum((allocation + maximum - 1) // maximum) > available_queries:
            active = np.flatnonzero(allocation)
            fractions[active[np.argmin(allocation[active])]] = 0
            fractions /= fractions.sum()
            allocation = integer_allocation(fractions, total)
        collect(allocation)
        information = np.einsum('a,akl->kl', model.spent, fisher) + np.eye(model.channels) * 0.1
        covariance = np.linalg.inv(information)
        fitted = model.fit(fitted, np.sqrt(np.diag(covariance)))
        print('stage', target, 'cpu', round(time.process_time(), 3), file=sys.stderr)
    information = np.einsum('a,akl->kl', model.spent, fisher) + np.eye(model.channels) * 0.1
    covariance = np.linalg.inv(information)
    gradient = model.fitted_gradient
    center = fitted - covariance @ gradient
    estimate, unused = posterior(center, covariance, model.bounds)
    print('final cpu', round(time.process_time(), 3), file=sys.stderr)
    return np.exp(estimate)


def main():
    spec = json.loads(sys.stdin.readline())['spec']

    def query(action, shots):
        print(json.dumps({'type': 'query', 'action': action, 'shots': shots}), flush=True)
        response = json.loads(sys.stdin.readline())
        if response.get('type') != 'observation':
            raise RuntimeError('Expected observation')
        return np.asarray(response['syndromes'], dtype=np.int64), np.asarray(response['multiplicities'], dtype=float)

    rates = calibrate(spec, query)
    print(json.dumps({'type': 'final', 'rates': rates.tolist()}, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()

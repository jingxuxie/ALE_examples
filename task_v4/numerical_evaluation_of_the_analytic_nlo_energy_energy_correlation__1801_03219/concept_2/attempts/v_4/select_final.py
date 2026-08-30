from highres import *
import subprocess


def main():
    best_witness=json.loads(Path('witness.json').read_text())
    best_report=verify(best_witness)
    print('INITIAL',best_report['worst'],flush=True)
    for prefix in (sys.argv[1:] or ['highres','tolerance','restart','edge']):
        filename=Path(prefix+'_best.npy')
        if not filename.exists():
            continue
        witness,masks,coefficients=np.load(filename,allow_pickle=True)
        candidate=quantize(witness,coefficients)
        report=verify(candidate)
        coefficient_limit=(1-2.4e-9)/abs(coefficients).sum()
        error_limit=min(entry['target']['tolerance']/entry['target']['estimated_error'] for entry in report['families'].values())
        nominal=min(coefficient_limit,error_limit)
        lower=max(1,nominal*.9)
        upper=min(coefficient_limit,nominal*1.12)
        scales=sorted(set([1.0,nominal]+np.linspace(lower,upper,61).tolist()))
        for scale in scales:
            candidate=quantize(witness,coefficients*scale)
            report=verify(candidate)
            if report['worst']>best_report['worst']:
                best_witness,best_report=candidate,report
                print('BEST',prefix,scale,report['worst'],report['mean'],flush=True)
    old=Path('witness.json').read_text().splitlines()
    new=(json.dumps(best_witness,indent=2)+'\n').splitlines()
    patch='*** Begin Patch\n*** Update File: witness.json\n@@\n'+''.join('-'+line+'\n' for line in old)+''.join('+'+line+'\n' for line in new)+'*** End Patch\n'
    subprocess.run(['apply_patch'],input=patch,text=True,check=True)
    Path('final_report.json').write_text(json.dumps(best_report,indent=2)+'\n')
    print('FINAL',best_report['worst'],best_report['mean'],flush=True)
    for family,entry in best_report['families'].items():
        print(family,'error',entry['error'],'reported',entry['target']['estimated_error'],'required',entry['required'],'margin',entry['margin'],flush=True)


if __name__=='__main__':
    main()

"""Render the architecture as an exact vector figure, not a system demonstration."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


def render(output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'font.size':8})
    fig,ax=plt.subplots(figsize=(7.15,2.65))
    ax.set(xlim=(0,10),ylim=(0,3.65)); ax.axis('off')
    def box(x,y,w,h,title,lines,kind='proposed'):
        implemented=kind=='implemented'
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.035,rounding_size=0.035',
            facecolor='#E8F1E8' if implemented else '#F4F5F5',
            edgecolor='#28633B' if implemented else '#45515B',
            linewidth=1.2 if implemented else .85,linestyle='--' if kind=='proposed' else '-'))
        ax.text(x+w/2,y+h-.13,title,ha='center',va='top',fontweight='bold',fontsize=8.1)
        ax.text(x+w/2,y+h-.43,'\n'.join(lines),ha='center',va='top',fontsize=7.4,linespacing=1.35)
    def arrow(a,b,label='',dy=.08):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=8,linewidth=.8,color='#34434D'))
        if label:ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+dy,label,ha='center',va='bottom',fontsize=7,
                         bbox={'facecolor':'white','edgecolor':'none','pad':.5})
    box(.12,.35,1.93,1.22,'Agent sandbox',['Untrusted reasoning','and tools'],kind='proposed')
    box(2.70,.35,2.16,1.22,'Proposal validator',['Schema + fixed context','Receipt only; no write'],kind='implemented')
    box(5.50,.19,2.38,1.56,'Effect service',['Authorization + freshness','Replay / rate controls','Scoped write credential'])
    box(8.55,.51,1.30,.89,'Target',['Repository object'],kind='resource')
    box(2.70,2.35,2.16,1.03,'Inference gateway',['Provider key outside agent','Destination / request limits'])
    box(5.50,2.35,2.38,1.03,'Execution / egress',['Fresh state; mediated paths','Audit and redaction'])
    ax.text(1.09,2.35,'Contributor text\nand files',ha='center',va='center',fontsize=8.2)
    arrow((1.09,2.0),(1.09,1.62))
    arrow((2.10,.96),(2.65,.96),'Proposal')
    arrow((4.91,.96),(5.45,.96),'Receipt')
    arrow((7.93,.96),(8.50,.96),'Apply')
    arrow((1.73,1.61),(2.84,2.30),'Inference',dy=.03)
    arrow((3.12,2.30),(1.96,1.61))
    arrow((6.69,2.30),(6.69,1.80))
    ax.text(5.18,.015,'All relevant effect paths must be mediated; bypass routes invalidate the scoping lemma.',
            ha='center',va='bottom',fontsize=7.4)
    fig.subplots_adjust(left=.008,right=.995,top=.99,bottom=.015)
    fig.savefig(output/'figure1.pdf',facecolor='white')
    fig.savefig(output/'figure1.svg',facecolor='white')
    fig.savefig(output/'figure1.png',dpi=300,facecolor='white')
    plt.close(fig)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(Path(__file__).parent))
    render(p.parse_args().output)

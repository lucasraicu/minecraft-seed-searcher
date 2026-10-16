#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
typedef struct {int n;int *xz;} NBPoints;
typedef struct {int x,z;} Pos;
static int floordiv(int x,int y){return x/y-(x%y<0);}
static int nb_dynamic_intcmp(const void *av,const void *bv) {
    int a=*(const int*)av,b=*(const int*)bv;return a<b?-1:a>b;
}
static void nb_dynamic_event(int *events,int *n,int value,int min_c,int max_c) {
    if(value>min_c&&value<=max_c)events[(*n)++]=value;
}
static int nb_dynamic_unique(int *events,int n) {
    qsort(events,(size_t)n,sizeof(int),nb_dynamic_intcmp);
    int k=0;for(int i=0;i<n;i++)if(!k||events[i]!=events[k-1])events[k++]=events[i];
    return k;
}
static int nb_dynamic_count(const NBPoints *points,int x,int z,int half,int nether,
                            const int *mansion_ids,int dark_id) {
    int n=0;
    for(int i=0;i<points->n;i++) {
        if(mansion_ids&&mansion_ids[i]!=dark_id)continue;
        int px=points->xz[2*i],pz=points->xz[2*i+1];
        if(nether ? (8*(px-half)<x&&x<=8*(px+half)&&8*(pz-half)<z&&z<=8*(pz+half)) :
                    (x-half<=px&&px<x+half&&z-half<=pz&&pz<z+half))n++;
    }
    return n;
}
static int64_t nb_dynamic_floor64(int64_t value,int64_t divisor) {
    int64_t q=value/divisor;return q-(value%divisor<0);
}
static int nb_dynamic_snap(int lo,int hi,int64_t sum,int weight,int step,int *value) {
    int lower=-floordiv(-lo,step)*step,upper=floordiv(hi,step)*step;
    if(lower>upper)return 0;
    int rounded=weight?(int)(nb_dynamic_floor64(sum+(step/2)*weight,(int64_t)step*weight)*step):0;
    *value=rounded<lower?lower:rounded>upper?upper:rounded;return 1;
}
static int nb_dynamic_raw_bounds_core(const int *fort,int nf,const int *bast,int nb,
                                      int fort_goal,int bast_goal,int *feasible,
                                      const Pos *mansions,int nm,int mansion_goal,int *overlap_out,
                                      int ow_half,int nether_half) {
    if(!fort||!bast||!feasible||nf<0||nb<0||nf>256||nb>256||fort_goal<1||bast_goal<1)return -1;
    if(nf<fort_goal||nb<bast_goal)return 0;
    if(ow_half<=0)ow_half=832;
    if(nether_half<=0)nether_half=416;
    int max_c = 2000 - ow_half;
    int min_c = -max_c;
    int xs[1030],zs[1030],nx=2,nz=2;
    xs[0]=zs[0]=min_c;xs[1]=zs[1]=max_c+1;
    for(int k=0;k<2;k++) {
        int n=k?nb:nf;const int *points=k?bast:fort;
        for(int i=0;i<n;i++) {
            nb_dynamic_event(xs,&nx,8*(points[2*i]-nether_half)+1,min_c,max_c);
            nb_dynamic_event(xs,&nx,8*(points[2*i]+nether_half)+1,min_c,max_c);
            nb_dynamic_event(zs,&nz,8*(points[2*i+1]-nether_half)+1,min_c,max_c);
            nb_dynamic_event(zs,&nz,8*(points[2*i+1]+nether_half)+1,min_c,max_c);
        }
    }
    nx=nb_dynamic_unique(xs,nx);nz=nb_dynamic_unique(zs,nz);
    NBPoints fp={nf,(int*)fort},bp={nb,(int*)bast};int xmin=max_c+1,zmin=max_c+1,xmax=min_c-1,zmax=min_c-1;
    int mansion_overlap=0;
    for(int ix=0;ix<nx-1;ix++)for(int iz=0;iz<nz-1;iz++) {
        int x=-floordiv(-xs[ix],8)*8,z=-floordiv(-zs[iz],8)*8;
        if(x>=xs[ix+1]||z>=zs[iz+1])continue;
        if(nb_dynamic_count(&fp,x,z,nether_half,1,NULL,0)<fort_goal ||
           nb_dynamic_count(&bp,x,z,nether_half,1,NULL,0)<bast_goal)continue;
        int hx=floordiv(xs[ix+1]-1,8)*8,hz=floordiv(zs[iz+1]-1,8)*8;
        if(x<xmin)xmin=x;if(z<zmin)zmin=z;if(hx>xmax)xmax=hx;if(hz>zmax)zmax=hz;
        if(mansion_goal>0 && mansions && nm>0 && !mansion_overlap) {
            for(int m=0;m<nm;m++) {
                if(mansions[m].x+ow_half>=x && mansions[m].x-(ow_half-1)<=hx &&
                   mansions[m].z+ow_half>=z && mansions[m].z-(ow_half-1)<=hz) {
                    mansion_overlap=1;
                    break;
                }
            }
        }
    }
    if(overlap_out)*overlap_out=mansion_overlap;
    if(xmin>xmax||zmin>zmax)return 0;
    feasible[0]=xmin-ow_half;feasible[1]=zmin-ow_half;feasible[2]=xmax+(ow_half-1);feasible[3]=zmax+(ow_half-1);
    return 1;
}
int main(void){srand(521);int snaps=200000;
for(int i=0;i<snaps;i++){int lo=rand()%1953-976,hi=lo+rand()%(977-lo),step=(i&1)?8:16,w=1+rand()%100;int64_t sum=(rand()%400001-200000);int v=9999;int ok=nb_dynamic_snap(lo,hi,sum,w,step,&v);int exists=0;for(int x=lo;x<=hi;x++)if(x%step==0)exists=1;assert(ok==exists);if(ok){assert(v>=lo&&v<=hi&&v%step==0);}}
for(int t=0;t<300;t++){int f[6],b[8],got[4];for(int i=0;i<6;i++)f[i]=rand()%1401-700;for(int i=0;i<8;i++)b[i]=rand()%1401-700;NBPoints fp={3,f},bp={4,b};int xmin=9999,zmin=9999,xmax=-9999,zmax=-9999;
for(int x=-976;x<=976;x+=8)for(int z=-976;z<=976;z+=8){int nf=0,nb=0;for(int i=0;i<3;i++)nf+=(x/8-512<=f[2*i]&&f[2*i]<x/8+512&&z/8-512<=f[2*i+1]&&f[2*i+1]<z/8+512);for(int i=0;i<4;i++)nb+=(x/8-512<=b[2*i]&&b[2*i]<x/8+512&&z/8-512<=b[2*i+1]&&b[2*i+1]<z/8+512);assert(nf==nb_dynamic_count(&fp,x,z,512,1,NULL,0));assert(nb==nb_dynamic_count(&bp,x,z,512,1,NULL,0));if(nf>=1&&nb>=2){if(x<xmin)xmin=x;if(x>xmax)xmax=x;if(z<zmin)zmin=z;if(z>zmax)zmax=z;}}
int ok=nb_dynamic_raw_bounds_core(f,3,b,4,1,2,got,NULL,0,0,NULL,1024,512);assert(ok==(xmin<=xmax));if(ok){assert(got[0]==xmin-1024&&got[1]==zmin-1024&&got[2]==xmax+1023&&got[3]==zmax+1023);}}
printf("200000 snap cases; 300 exhaustive 245x245 Nether co-window grids; no assertion failures\n");return 0;}

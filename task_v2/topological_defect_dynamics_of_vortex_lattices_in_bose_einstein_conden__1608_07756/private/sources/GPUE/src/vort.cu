#include "../include/vort.h"


//@todo Implement this
namespace Vtx {

    Vortex::Vortex():uid(-1){ }
    Vortex::Vortex(int2 coords, double2 coordsD, int winding, bool isOn, std::size_t timeStep):uid(-1){
        this->coords = coords; //Coords to the grid
        this->coordsD = coordsD; //Subgrid coords
        this->winding = winding; //Charge of vortex
        this->isOn = isOn; //Whether the vortex still exists, or has died/gone outside boundary
        this->timeStep = timeStep;
    }
    Vortex::~Vortex(){ }

    void Vortex::updateUID(int uid){
        this->uid = uid;
    }
    void Vortex::updateWinding(int winding){
        this->winding = winding;
    }
    void Vortex::updateIsOn(bool isOn){
        this->isOn = isOn;
    }
    void Vortex::updateCoords(int2 coords){
        this->coords = coords;
    }
    void Vortex::updateCoordsD(double2 coordsD){
        this->coordsD = coordsD;
    }
    void Vortex::updateTimeStep(std::size_t timeStep){
        this->timeStep = timeStep;
    }

    int Vortex::getUID() const{
        return this->uid;
    }
    int Vortex::getWinding() const{
        return this->winding;
    }
    bool Vortex::getIsOn() const{
        return this->isOn;
    }
    int2 Vortex::getCoords() const{
        return this->coords;
    }
    double2 Vortex::getCoordsD() const{
        return this->coordsD;
    }
    std::size_t Vortex::getTimeStep() const{
        return this->timeStep;
    }


//######################################################################################################################
//######################################################################################################################

    VtxList::VtxList():suid(0) {
    }
    VtxList::VtxList(std::size_t reserveSize):suid(0) {
        vortices.reserve(reserveSize);
    }
    VtxList::~VtxList() {
        this->getVortices().clear();
    }

    //Add vortex to end of list.
    void VtxList::addVtx(std::shared_ptr<Vtx::Vortex> vtx) {
        this->suid++;
        this->getVortices().push_back(vtx);
    }
    //Add vortex to list at the given idx
    void VtxList::addVtx(std::shared_ptr<Vtx::Vortex> vtx, std::size_t idx) {
        vtx->updateUID(++this->suid);
        this->getVortices().insert(this->vortices.begin() + idx, vtx);
    }

    //Will return nullptr if idx is outside the range. Otherwise, removes element at idx, and returns a shared_ptr to it
    std::shared_ptr<Vtx::Vortex> VtxList::removeVtx(size_t idx) {
        std::shared_ptr<Vtx::Vortex> v = nullptr;
        if(idx < this->vortices.size()){
             v = this->vortices[idx];
            this->vortices.erase(VtxList::vortices.begin() + idx);
        }
        return v;
    }

    std::vector<std::shared_ptr<Vtx::Vortex> >& VtxList::getVortices(){
        return this->vortices;
    }

    //Assumes UID exists.
    std::shared_ptr<Vtx::Vortex> VtxList::getVtx_Uid(int uid){
        for(auto a : this->vortices){
            if(a->getUID() != uid){
                continue;
            }
            else
                return a;
        }
        return nullptr;
    }

    std::shared_ptr<Vtx::Vortex> VtxList::getVtx_Idx(std::size_t idx) {
        return this->vortices[idx];
    }

    //Assumes UID exists
    std::size_t VtxList::getVtxIdx_Uid(int uid){
        for(std::size_t t = 0; t < this->vortices.size(); ++t){
            if(this->vortices[t]->getUID() != uid){
                continue;
            }
            else
                return t;
        }
    }

    std::size_t& VtxList::getMax_Uid(){
        return this->suid;
    }

    //Compare the distances between vtx and the vortex list. Used for time-based tracking
    std::shared_ptr<Vtx::Vortex> VtxList::getVtxMinDist(std::shared_ptr<Vortex> vtx){
        double dist = std::numeric_limits<double>::max(), distTmp=0.; // Start large
        double2 pos0 = vtx->getCoordsD(), pos1;
        std::size_t idx=0;
        for(std::size_t i=0; i < this->vortices.size(); ++i){
            pos1 = this->vortices[i]->getCoordsD();
            distTmp = sqrt(pow(pos0.x-pos1.x,2) + pow(pos0.y - pos1.y,2));
            if( dist > distTmp && distTmp > 0){
                dist = distTmp;
                idx = i;
            }
        }
        return this->vortices[idx];
    }

    void VtxList::swapUid(std::shared_ptr<Vtx::Vortex> v1, std::shared_ptr<Vtx::Vortex> v2){
        std::size_t uid1 = v1->getUID();
        v1->updateUID(v2->getUID());
        v2->updateUID(uid1);
    }

    void VtxList::swapUid_Idx(std::size_t idx0, std::size_t idx1){
        std::size_t uid0 = this->vortices[idx0]->getUID();
        this->vortices[idx0]->updateUID(this->vortices[idx1]->getUID());
        this->vortices[idx1]->updateUID(uid0);
    }

    void VtxList::sortVtxUID(){
        std::sort(this->getVortices().begin(), this->getVortices().end(),
             [](std::shared_ptr<Vtx::Vortex> v0, std::shared_ptr<Vtx::Vortex> v1)
                     ->
                     bool{
                 return (v0->getUID() < v1->getUID());
             }
        );
    }

    void VtxList::setUIDs(std::set<std::shared_ptr<Vtx::Vortex> > &v){
        for (auto e : this->getVortices()){
            if(1){

            }
        }
    }

    void VtxList::arrangeVtx(std::vector<std::shared_ptr<Vtx::Vortex> > &vPrev){
        std::set<std::shared_ptr<Vtx::Vortex> > sVtx_d01, sVtx_d10, sVtx_inter;
        //Find the intersection of the UIDs, as well as elements unique to prev or current
        std::set_intersection(
                this->getVortices().begin(), this->getVortices().end(),
                vPrev.begin(), vPrev.end(),
                std::inserter(sVtx_inter,sVtx_inter.begin()),
                [](std::shared_ptr<Vtx::Vortex> v0, std::shared_ptr<Vtx::Vortex> v1)
                        ->
                        bool{
                    return (v0->getUID() < v1->getUID());
                }
        );
        std::set_difference(
                this->getVortices().begin(), this->getVortices().end(),
                vPrev.begin(), vPrev.end(),
                std::inserter(sVtx_d01,sVtx_d01.begin()),
                [](std::shared_ptr<Vtx::Vortex> v0, std::shared_ptr<Vtx::Vortex> v1)
                        ->
                        bool{
                    return (v0->getUID() < v1->getUID());
                }
        );
        std::set_difference(
                vPrev.begin(), vPrev.end(),
                this->getVortices().begin(), this->getVortices().end(),
                std::inserter(sVtx_d10,sVtx_d10.begin()),
                [](std::shared_ptr<Vtx::Vortex> v0, std::shared_ptr<Vtx::Vortex> v1)
                        ->
                        bool{
                    return (v0->getUID() < v1->getUID());
                }
        );

        std::cout << "####Inter####\n";
        for (auto e : sVtx_inter){
            std::cout << (e)->getUID() << std::endl;
        }
        std::cout << "####Diff01####\n";
        for (auto e : sVtx_d01){
            std::cout << (e)->getUID() << std::endl;
        }
        std::cout << "####Diff10####\n";
        for (auto e : sVtx_d10){
            std::cout << (e)->getUID() << std::endl;
        }
        std::cout << "#######\n";


    }

    /* Generate and return a pairing of the distance and closest vortex to vtx */
    std::pair<double,std::shared_ptr<Vortex>> VtxList::minDistPair(std::shared_ptr<Vortex> vtx, double minRange){
        /* Ensure the vortex is turned on in the previous run. If not, cannot find a corresponding vortex */
        if(!vtx->getIsOn())
            return {-1.,nullptr};

        /* Vortices are paired with their distance to the respective test candidate vtx */
        std::vector< std::pair<double, std::shared_ptr<Vortex>> > r_uid;
        r_uid.reserve(this->getVortices().size());

        /* Lambda for pairing the vortices and distances */
        auto pairRDist = [&vtx,&r_uid](VtxList *vL) {
            for (auto v : vL->getVortices()) {
                r_uid.push_back(
                        std::make_pair(
                                pow(v->coordsD.x - vtx->coordsD.x, 2)
                                +
                                pow(v->coordsD.y - vtx->coordsD.y, 2),
                                v
                        )
                );
                //std::cout << "UIDin=" << vtx->getUID() << " UIDout=" << v->getUID() << " R=" << pow(v->coordsD.x - vtx->coordsD.x, 2) + pow(v->coordsD.y - vtx->coordsD.y, 2) << "\n" ;
            }
        };
        pairRDist(this);

        /* Lambda for comparison of the vortex distances, to return the vortex with minimum distance */
        auto compMin = [](  std::pair<double,std::shared_ptr<Vortex> >& p0,
                            std::pair<double,std::shared_ptr<Vortex> >& p1
                        ) -> double {
                                return p0.first < p1.first;
        };

        /* Need to ensure that the vortex is within the minimal allowed distance for pairing.
         * Outside of this range, the vortex is considered a different vortex, and so returns
         * a nullptr, meaning that no vortex is found. */
        auto pairMin = std::min_element( r_uid.begin(), r_uid.end(), compMin);
        return {pairMin->first,(pairMin->first <= minRange && pairMin->second->getWinding() == vtx->getWinding()) ? pairMin->second : nullptr};
    }




    /*void VtxList::increaseList(){
    }*/
}

